"""
For a given block visit, calculate the slew time, acquisition time, and science time based on
data in the SDB
"""
import sys 
import time 
import datetime 
import string
import numpy as np

import mysql

def getnightinfo(sdb, obsdate):
    return sdb.select('NightInfo_Id', 'NightInfo', 'Date=%s' % obsdate)[0][0]


def blockvisitstats(sdb, obsdate, update=True):
   """Determine the block visit statistics for an observation date.  These 
      statistics include slew time, acquisition time, and total science 
      time for the block.   For rejected blocks, this includes the time
      until the next pointing 

      Parameters
      ----------

      sdb: mysql-instance
           sdb is a connection to the science data base
      obsdate: string
           observation date of interest

   """
 
   #for a given obsdate get the night info
   nid=getnightinfo(sdb, obsdate)

   #get the times for the night
   record=sdb.select('EveningTwilightEnd, MorningTwilightStart', 'NightInfo', 'NightInfo_Id=%i' % nid)
   stime=record[0][0]
   etime=record[0][1]
   totaltime=(etime-stime).seconds
   #From the sdb, get the SoLogEvent table
   record=sdb.select('EventType_Id, EventTime', 'SoLogEvent', 'NightInfo_Id=%i' % nid)
   event_list=[]
   for i in range(len(record)):
       r=record[i]
       if r[1].seconds>43200:
          t=datetime.datetime(int(obsdate[0:4]), int(obsdate[4:6]), int(obsdate[6:8]), 0, 0, 0)+r[1]
       else:
          t=datetime.datetime(int(obsdate[0:4]), int(obsdate[4:6]), int(obsdate[6:8]), 0, 0, 0)+datetime.timedelta(days=1)+r[1]
       event_list.append([r[0], t])

   #sort the list by the datetimes
   event_list.sort(key=lambda e:e[1])

   #get the list of accepted blocks
   selcmd='BlockVisit_Id, Accepted, Proposal_Code, Block_Id'
   tabcmd='Block join BlockVisit using (Block_Id) join Proposal using (Proposal_Id) join ProposalCode using (ProposalCode_Id)'
   blocks=sdb.select(selcmd, tabcmd, 'NightInfo_Id=%i' % nid)
   blocks=list(blocks)
   #print blocks

   #list of accepted blocks
   pid_list=[]
   rej_list=[]
   for b in blocks: 
       if b[1]==1: 
          pid_list.append(b[2])
       else:
          rej_list.append(b[2])

   #print pid_list
   #print rej_list
       
   #get a list of all data from the night
   select_state='FileName, Proposal_Code, Target_Name, ExposureTime, UTSTART, h.INSTRUME, h.OBSMODE, h.DETMODE, h.CCDTYPE, NExposures, Block_Id'
   table_state='FileData  Join ProposalCode using (ProposalCode_Id) join FitsHeaderImage as h using (FileData_Id)'
   logic_state="FileName like '%"+obsdate+"%' order by FileName"
   img_list=sdb.select(select_state, table_state, logic_state)

   #now create a list of all pointing commands
   point_list=[]
   for r in event_list:
       if r[0]==3: point_list.append(r[1])

   #for b in blocks: if b[1]==3: blocks.remove(b)

   #now loop through that list and associate each pointing with a blocks
   block_list=[]
   blocks_orig = list(blocks)
   print blocks
   for point in point_list:
       starttime=point
       endtime=findnextpointing(starttime, event_list, etime)
       #now find any date sets that might be associated with this date and time
       #and the data and times 
       propcode, target, bid, instr, obsmode, detmode, exptime, nexposure = finddata(img_list, starttime, endtime)
       bvid = get_blockvisitfrompointtime(sdb, starttime, propcode)
       #print propcode, target, bid, instr, obsmode, detmode, exptime, nexposure
       #print starttime, endtime, propcode, target
       if propcode in pid_list and not (propcode in rej_list): 
           blocks = removepropcode(blocks, propcode)
           block_list.append([bvid, starttime, endtime, 0, propcode])
       elif propcode in rej_list and not (propcode in pid_list):
           status = getblockrejectreason(sdb, propcode, blocks)
           block_list.append([bvid, starttime, endtime, status, propcode])
       elif propcode in pid_list and propcode in rej_list:
           #get the first block with the propcode
           for b in blocks:
               if b[0]==bvid:
                  if b[1]==1:
                     status=0
                  else:
                     status = getblockrejectreason(sdb, propcode, blocks)
                  #print starttime, endtime, propcode, target, bid, status
                  block_list.append([bvid, starttime, endtime, status, propcode])
                  #blocks = removepropcode(blocks, propcode)
                    
  
       #determine statistics associated with accepted block
       if propcode in pid_list and bid is not None:
           #print bid, propcode
           #deal with accepted blocks
           #determine total time
           tottime=endtime-starttime
           #determine the slew time
           guidestart=findguidingstart(starttime, event_list)
           slewtime=guidestart-starttime
           #determine the science time
           instr, primary_mode=getprimarymode(img_list, bid)
           if instr=='HRS': continue

           sciencestart=getfirstimage(img_list, starttime,  instr, primary_mode)
           if sciencestart is None: continue
           scitime=endtime-sciencestart

           #determine the acquisition time
           acqtime=sciencestart-guidestart

           #determine the block visit
           bvid=getblockvisit(blocks_orig, bid)
           #print bvid
           #print starttime, endtime, propcode, target, bid, bvid, slewtime, acqtime, scitime, tottime
           #upload results to sdb 
           #print propcode, bvid, slewtime, acqtime, scitime
           if bvid is not None and update:
               inscmd='TotalSlewTime=%i, TotalAcquisitionTime=%i, TotalScienceTime=%i' % (slewtime.seconds, acqtime.seconds, scitime.seconds)
               sdb.update(inscmd, 'BlockVisit', 'BlockVisit_Id=%i' % bvid)

       elif propcode is not None and bid is not None:
           #deal with rejected block
           pass
       elif propcode is not None and bid is None:
           #deal with commissioning blocks
           pass
       else:
           #otherwise ignore
           pass    
       


   return block_list

def removepropcode(blocks, propcode):
    for b in blocks:
        if b[2]==propcode:
           blocks.remove(b)
           return blocks
    return blocks

def get_blockvisitfrompointtime(sdb, starttime, propcode=None):
    table = 'PointEvent join SoLogEvent using (SoLogEvent_Id)'
    logic = 'EventTime="{}"'.format(starttime)
    if propcode is not None and propcode!='JUNK' and not propcode.count("CAL_") and not propcode.count("ENG_"): 
        logic += ' and Proposal_Code="{}"'.format(propcode)
    print sdb.select('BlockVisit_Id', table, logic)
    print starttime, propcode
    return sdb.select('BlockVisit_Id', table, logic)[0][0]


def getblockrejectreason(sdb, propcode, blocks):
    """Get the reason for the block rejection"""
    for b in blocks:
        if propcode == b[2]: 
           record = sdb.select('BlockRejectedReason_Id', 'BlockVisit', 'BlockVisit_Id=%i' % b[0])[0][0]
           return record
    return 0

def getblockvisit(blocks, bid, accept=1):
    for b in blocks:
        if b[3]==bid and b[1]==accept: return b[0]
    return None
 

def getfirstimage(image_list, starttime, instr, primary_mode):
   """Determine the first image of a list that has that 
      mode in use

   """
   stime=starttime-datetime.timedelta(seconds=2*3600.0)
   for img in image_list:
       if instr=='RSS':
           if img[4]>stime and img[6]==primary_mode: 
              return img[4]+datetime.timedelta(seconds=2*3600.0)
       elif instr=='HRS':
           if img[4]>stime and img[6]==primary_mode:
              return img[4]+datetime.timedelta(seconds=2*3600.0)
       elif instr=='SCAM':
           if img[4]>stime and img[7]==primary_mode: return img[4]+datetime.timedelta(seconds=2*3600.0)
   return None


def getprimarymode(image_list, bid):
   """Determine the primary mode of the science frame for the block

   """
   primary_mode=None
   instr=[]
   obsmode=[]
   detmode=[]
   for img in image_list:
       if img[10]==bid:
          instr.append(img[5])
          obsmode.append(img[6])
          detmode.append(img[7])

   #set the instrument
   if 'RSS' in instr:
       instr='RSS'
   elif 'HRS' in instr:
       instr='HRS'
   else:
       instr='SCAM'

   #set the mode
   if instr=='RSS':
      if 'SPECTROSCOPY' in obsmode: 
         primary_mode='SPECTROSCOPY'
      elif 'FABRY-PEROT' in obsmode:
         primary_mode='FABRY-PEROT'
      else:
         primary_mode='IMAGING'
   elif instr=='HRS':
      primary_mode = obsmode[0]
   elif instr=='SCAM':
      if 'SLOTMODE' in detmode:
         primary_mode='SLOTMODE'
      else:
         primary_mode='NORMAL'

   return instr, primary_mode
   

def findguidingstart(starttime, event_list):
   """Determine when guiding starts from the next guiding command 
      in the event list
   """
   for r in event_list:
       if r[0]==5 and r[1]>starttime: return r[1]
   return None 

def finddata(img_list, starttime, endtime):
    """Determine if any data were taken between 
       start time and endtime
    """
    #convert to UT
    stime=starttime-datetime.timedelta(seconds=2*3600.0)
    etime=endtime-datetime.timedelta(seconds=2*3600.0)
    for img in img_list:
       if img[4] is not None:
           if img[4]>stime and img[4]<etime and img[2] not in ['ARC', 'FLAT']: 
               return img[1], img[2], img[10], img[5], img[6], img[7], img[3], img[9]
    
    return [None]*8 

def findnextpointing(starttime, record, etime=None):
   """The next pointing occurs either when the next point to target
      command happens
   """
   for r in record:  
       if (r[0]==3 or r[0]==10) and r[1]>starttime: return r[1]
   return etime
