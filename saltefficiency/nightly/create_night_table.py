
import string
import datetime

import numpy as np

import pylab as pl
from matplotlib.patches import Rectangle

import saltefficiency.util.blockvisitstats as bvs
import saltefficiency.util.sdb_utils as su


def create_night_table(obsdate, sdb, els):
    """Create a table that shows a break down for the night and what happened in each block

    Parameters
    ----------
    nid: int
        NightInfo_Id

    sdb: ~mysql.mysql
       A connection to the sdb database

    els: ~mysql.mysql
       A connection to the els database

    """

    # create a dictionary to break down the events of the night
    night_dict = {}
    nid = su.getnightinfo(sdb, obsdate)

    #get the times for the night
    record=sdb.select('EveningTwilightEnd, MorningTwilightStart', 'NightInfo', 'NightInfo_Id=%i' % nid)
    stime=record[0][0]
    etime=record[0][1]
    totaltime=(etime-stime).seconds
    night = Night(nid, stime, etime)

    #get the SO event log
    record=sdb.select('EventType_Id, EventTime', 'SoLogEvent', 'NightInfo_Id=%i' % nid)

    #set it up wtih the correct time
    event_list=[]
    for i in range(len(record)):
        t=record[i][1].seconds
        #convert to times from the observing day
        if t < 12*3600:
           t+=12*3600
        else:
           t-=12*3600
        event_list.append([record[i][0],t])

    # add weather down time to night_dict
    time_list,wea_arr = create_weather(els, stime, etime)
    night.add_weather(time_list, wea_arr)

    # add the accepted blocks to night_dict
    block_list=bvs.blockvisitstats(sdb, obsdate, update=False)
    for b in block_list:
        print b
        night_dict[b[1]] = ['Science', b]
    night.add_blocks(block_list)

    # add fault down time to the night_dict
    faults = create_faults(sdb, nid)
    problem_list=[]
    for f in faults:
        t1 = (f[1]-night.day_start).seconds
        t2 = (f[2]-night.day_start).seconds
        problem_list.append([t1, t2])
        print f
        night_dict[f[1]] = ['Fault', f]
    night.add_problems(problem_list)



    # add mirror alignment to the night_dict
    mirror_alignment=create_mirror_alignment(event_list)
    night.add_mirroralignment(mirror_alignment)
    for m in mirror_alignment:
        t1 = convert_decimal_hours(obsdate, m[0]/3600.0)
        night_dict[t1] = ['Mirror', m]


    # use the dict to populate the table to display what did happen
    night.calc_engineering()
    night.calc_weather()

    #night.plot()
    info_txt="""
    Total Time: {5:0.2f} <br>
    Science Time: {0:0.2f} <br>
    Engineering TIme: {4: 0.2f} <br>
    Weather Time: {1:0.2f} <br>
    Time Lost to Problems: {3:0.2f} <br>\n
    <br>
    Mirror Alignment Time: {2:0.2f} <br>\n
""".format(night.sciencetime, night.weathertime, night.mirroralignmenttime, night.problemtime, night.engineertime, night.totaltime/3600.0)

    table_txt ='<p><table>'
    table_txt +='<tr><th>Time</th><th>Type</th><th>Length</th><th>Comment</th></tr>\n'
    status = 0
    start = None
    for i in range(len(night.status_arr)):
        if start is not None and night.status_arr[i]!=status:
           table_txt += create_row(sdb, start, i, night_dict, night, obsdate)
           start=None
        if night.status_arr[i]>0 and start is None:
           status = night.status_arr[i]
           start = i

    table_txt +='</table></p>\n'
    return  info_txt + table_txt

def create_row(sdb, sid, eid, night_dict, night, obsdate):
    """Create a row with all the information for that block
    """
    status = night.status_arr[sid]

    t1 = convert_decimal_hours(obsdate, night.time_arr[sid])
    t2 = convert_decimal_hours(obsdate, night.time_arr[eid])


    l=(t2-t1).seconds/3600.0
    length='{0}:{1}'.format(int(l), string.zfill(int(60.0*(l-int(l))),2))

    #find the key
    min_time = 600
    block_time = None
    t0 = convert_decimal_hours(obsdate, 1.0)
    for k in night_dict.keys():
        t = (t1 - t0).seconds - (k-t0).seconds
        if abs(t) < min_time:
           block_time = k
           min_time = abs(t)

    keys = night_dict.keys()

    #create the row
    fgcolor='#000000'
    if status==1: fgcolor='#FFFFFF'
    row_str='<tr height={5}><td>{0}<br>{1}</td><td bgcolor="{2}"><font color="{4}">{3}</font></td>'.format(t1, t2, night.color_list[status], night.statusname_list[status], fgcolor, 50*l)
    row_str+='<td>{0}</td>'.format(length)
    if status==1:
       b = night_dict[block_time][1]
       print b
       row_str+='<td>{0}</td>'.format(b[4])
    row_str+='</tr>\n'
    return row_str

def convert_decimal_hours(obsdate, t1):
    """Convert decimal hours to a date time"""
    if t1 < 12:
       t1 = '{} {}:{}'.format(obsdate, int(t1), int(60*(t1-int(t1))))
       t1 = datetime.datetime.strptime(t1, '%Y%m%d %H:%M')
       t1 = t1+datetime.timedelta(seconds=12*3600)
    else:
       t1 = '{} {}:{}'.format(obsdate, int(t1-12), int(60*(t1-int(t1))))
       t1 = datetime.datetime.strptime(t1, '%Y%m%d %H:%M')
       t1 = t1+datetime.timedelta(seconds=24*3600)
    return t1


def create_faults(sdb, nid):
    """Return a list of information about the faults

    """
    select = 'Fault_id, FaultStart, FaultEnd, TimeLost, SaltSubsystem'
    tables = 'Fault join SaltSubsystem using (SaltSubsystem_Id)'
    logic = 'NightInfo_Id={} and TimeLost > 0'.format(nid)
    return sdb.select(select, tables, logic)

def create_weather(els, stime, etime):
    """Return an array of times that the weather was bad
    """
    weather_info = su.get_weather_info(els, stime, etime)
    time_list, air_arr, dew_arr, hum_arr, w30_arr, w30d_arr, w10_arr, \
    w10d_arr, rain_list, t02_arr, t05_arr, t10_arr, t15_arr, t20_arr, \
    t25_arr, t30_arr = weather_info

    #need to include other/better limits
    wea_arr = (hum_arr>85.0)
    return time_list, wea_arr

def create_mirror_alignment(event_list):
    """Determine the mirror alignment time
    """
    mirror_list=[]
    mirror_start=False
    for r in event_list:
        if r[0]==10 and mirror_start==False:
           t=r[1]
           #use the time from the
           if old_event[0] in [4, 6, 13, 14]: t=old_event[1]
           mirror_start=[t]
        if mirror_start:
           if r[0] in [3,5]:
              t=r[1]
              mirror_start.append(t)
              mirror_list.append(mirror_start)
              mirror_start=False
        old_event = r
    return mirror_list




class Night:
   def __init__(self, nid, night_start, night_end):
       self.nid=nid
       self.night_start = night_start
       self.night_end = night_end
       self.totaltime=(self.night_end-self.night_start).seconds
       self.sciencetime=0
       self.engineertime=0
       self.weathertime=0
       self.problemtime=0
       self.shuttertime=0
       self.mirroralignmenttime=0
       self.dt=0.1

       #set up arrays to represent different events
       self.time_arr =  np.arange(0,24,self.dt) #array representing time since noon that day
       self.day_start = datetime.datetime(self.night_start.year, self.night_start.month, self.night_start.day, 12,0,0)
       self.night_time = (self.time_arr > (self.night_start-self.day_start).seconds/3600.0) * ( self.time_arr < (self.night_end-self.day_start).seconds/3600.0)
       self.status_arr = np.zeros(len(self.time_arr), dtype=int)
       self.stime = (self.night_start-self.day_start).seconds/3600.0
       self.etime = (self.night_end-self.day_start).seconds/3600.0

       #set color and name list
       self.statusname_list=['none', 'Science', 'Engineer', 'Weather', 'Problem', 'Rejected']
       self.color_list=['none', 'blue', 'green', 'purple', 'red','yellow'] #none, science, engineer, weather, problem, rejected

   def add_weather(self, time_list, wea_arr):
       """Add the weather to the status array and weather
          the telescope is closed for weather or not

          time_list is in seconds since the start of the night
       """
       nstart = (self.night_start-self.day_start).seconds

       for i in range(len(time_list)):
           if wea_arr[i]:
              t = int((nstart + time_list[i])/3600.0/self.dt)
              self.status_arr[t]=3
       return

   def add_mirroralignment(self, mirror_list):
       """Add the mirror alignment to the status array
       """

       for t1,t2 in mirror_list:
           t1=t1/3600.0
           t2=t2/3600.0
           if t1 > self.stime and t1 < self.etime:
              self.mirroralignmenttime += t2-t1
              print t1, t2, self.stime, self.etime, self.mirroralignmenttime
              mask = (self.time_arr>t1)*(self.time_arr<t2)
              mid = np.where(mask)[0]
              self.status_arr[mid] = 2

   def add_problems(self, problems_list):
       """Add the problems to the status array
       """

       for t1,t2 in problems_list:
           t1=t1/3600.0
           t2=t2/3600.0
           if t1 > self.stime and t1 < self.etime:
              et2 = min(t2, self.etime)
              self.problemtime += et2-t1
              mask = (self.time_arr>t1)*(self.time_arr<t2)
              mid = np.where(mask)[0]
              self.status_arr[mid] = 4

   def add_blocks(self, block_list):
       """Add science time blocks to the status array
       """
       for bvid, t1,t2,stat, propcode in block_list:
           t1 =  (t1- self.day_start).seconds/3600.0
           t2 =  (t2- self.day_start).seconds/3600.0
           et1 = max(self.stime, t1)
           if t1 < self.etime:
              et2 = min(t2, self.etime)
              mask = (self.time_arr>t1)*(self.time_arr<t2)
              mid = np.where(mask)[0]
              if stat==0:
                  self.sciencetime += et2-et1
                  self.status_arr[mid] = 1
              else:
                  self.status_arr[mid] = 5
                  if stat==3: self.weathertime += et2-et1
                  if stat<3:
                     pass #self.problemtime += et2-et1
                     #print 'reject', self.problemtime, et2,et1

   def calc_engineering(self):
       for i in range(len(self.time_arr)):
           if self.time_arr[i]>self.stime and self.time_arr[i]<self.etime:
              if self.status_arr[i]==2 or self.status_arr[i]==0:
                 self.engineertime += self.dt

   def calc_weather(self):
       for i in range(len(self.time_arr)):
           if self.time_arr[i]>self.stime and self.time_arr[i]<self.etime:
              if self.status_arr[i]==3:
                 self.weathertime += self.dt

   def plot(self):

       color_list=['none', 'blue', 'green', 'purple', 'red','yellow'] #none, science, engineer, weather, problem, rejected
       pl.figure()
       ax=pl.axes([0.1,0.1,0.8,0.8])
       #add nightiime patch
       ax.add_patch(Rectangle((self.stime,0),self.totaltime/3600.0,4, alpha=0.3))

       #add status patches
       for i in range(len(self.status_arr)):
          if self.status_arr[i]>0:
             color=color_list[self.status_arr[i]]
             ax.add_patch(Rectangle((self.time_arr[i],1),self.dt,0.5, alpha=1.0, facecolor=color, edgecolor=color)) #color_list[self.status_arr[i]]))

       ax.axis([7,17,1,1.5])
       pl.show()

