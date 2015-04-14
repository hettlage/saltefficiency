# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 14:58:39 2015

@author: jpk

This script produces a report of observations taken the last 7 days at SALT
and print it out on the terminal and writes it to a file.

The script runs from today and queries the sdb for data going back 7 days.

"""

import os
import sys
import pandas as pd
import pandas.io.sql as psql
import MySQLdb
import matplotlib.pyplot as pl
import numpy as np
from datetime import datetime
import saltefficiency.util.report_queries as rq
import getopt


def string_header(dr):
    '''
    format the header to be printed and written to file
    '''
    s = dr.ix[0].to_string().split('\n')

    txt = '''
*************** SALT Weekly Observing Stats *****************
A report for %s to
             %s
    ''' %(s[0], s[1])

    return txt

def string_weekly_total_time_breakdown(wttb):

    # determine the percantages of time broken down in catagories
    t = pd.Series(wttb.stack(), index = wttb.stack().index)
    t.index = t.index.get_level_values(1)
    per = pd.Series(np.zeros(len(t)), index = t.index)
    per['Weather':'Science'] = t['Weather':'Science'] / t.Total * 100
    per['TimeLostToWeather': 'ScienceTime'] = per['Weather':'Science']

    # write out the string:
    txt = '''
-------------------------------------------------------------
Time Breakdown:
---------------

Science time:      {} ({:,.0f}%)
Engineering time:  {} ({:,.0f}%)
Weather:           {} ({:,.0f}%)
Problems:          {} ({:,.0f}%)
--
Total:             {}

'''.format(t.ScienceTime, per.Science,
        t.EngineeringTime, per.Engineering,
        t.TimeLostToWeather, per.Weather,
        t.TimeLostToProblems, per.Problems,
        t.NightLength)

    return txt


def string_weekly_priority_breakdown(wpb):

    # create a percentage column
    wpb['per'] = pd.Series(np.zeros(len(wpb)), index = wpb.index)
    # determine the percentage from the Time column which is in seconds
    wpb.per = (wpb.Tsec / wpb.Tsec.sum()) * 100

    txt = wpb.to_string(columns=['Priority', 'No. Blocks', 'per'],
                         index=False,
                         header=False,
                         formatters={'per':'({:,.0f}%)'.format,
                                     'Priority':'   {:>5}      '.format,
                                     'No. Blocks':'   {0:,.0f}     '.format})

    hdr = '''
-------------------------------------------------------------
Priority BreakDown:
-------------------

Priority  No. Blocks
'''

    ftr = '''
--
Total             {0:,.0f}
    '''.format(wpb['No. Blocks'].sum())

    return hdr + txt + ftr

def string_weekly_subsystem_breakdown(wsb):

    # calculate the percentage of time breakdown
    # create a new percentage column
    wsb['per'] = pd.Series(np.zeros(len(wsb)), index = wsb.index)
    # determine the percentage from the Time column which is in seconds
    wsb.per = (wsb.Time / wsb.Time.sum()) * 100

    # create a string object to be printed and written to file
    txt = wsb.to_string(columns=['SaltSubsystem', 'TotalTime', 'per'],
                        index=False,
                        header=False,
                        formatters={'SaltSubsystem':'  {:>11}   '.format,
                                    'per':'({:,.0f}%)'.format,
                                    'TotalTime':' {} '.format })
    hdr = '''
-------------------------------------------------------------
Problems Time Breakdown
---------------------

SALT Subsystem  Total Time
'''

    return hdr + txt


def print_to_screen(txt):
    '''
    this function prints the formatted string to the terminal
    '''
    ftr = '''

****************** End of Weekly Report *********************
'''
    print txt + ftr

    return

def write_to_file(dr, txt, dirname='./logs/'):
    '''
    this function writes the text to a file and names the report accorting
    to the date range specified
    '''

    filename = 'weekly_report_' + datetime.strftime(dr.StartDate[0], '%Y%m%d') + \
               '-' + datetime.strftime(dr.EndDate[0], '%Y%m%d') + '.txt'

    ftr = '''

****************** End of Weekly Report *********************
'''

    with open(dirname+filename, 'w') as f:
        f.write(txt + ftr)

def commandLine(argv):
    # executes if module is run from the command line

#    Testing a datetime check
#    if type(arg) is not datetime.date:
#        raise TypeError('arg must be a datetime.date, not a %s' % type(arg))
    dprint("Reading command line options")

    # read command line options
    try:
        opts,args = getopt.getopt(sys.argv[1:],"vdct:f:i:r:o",
                ["sdate=","edate=","date=", "interval=","filter=","instrument=","radius=","ocs","help"])
    except getopt.GetoptError, inst:
        print inst
        print 'Use --help to get a list of options'
        sys.exit(2)


    # parse them to the relevant variables
    for opt, arg in opts:
        if opt in ('--help'):
            usage()
        elif opt in ('-v','--verbose'):
            verbose=True
        elif opt in ('-d','--debug'):
            verbose=True	# implied
            debug=True
        elif opt in ('-f','--filter'):
            filter = arg
        elif opt in ('-i','--instrument'):
            ins = arg
        elif opt in ('-r','--radius'):
            radius = float(arg)
        elif opt in ('-t','--target-id'):
            target_id = arg
        elif opt in ('-c','--current'):
            use_current_pointing = True
        elif opt in ('-o','--ocs'):
            use_ocs = True
        else:
            print 'Unknown option: ' + opt
            usage()

if __name__=='__main__':

    # open mysql connection to the sdb
    mysql_con = MySQLdb.connect(host='sdb.cape.saao.ac.za',
                port=3306, user=os.environ['SDBUSER'],
                passwd=os.environ['SDBPASS'], db='sdb')

    obsdate = sys.argv[1]
    date = '{}-{}-{}'.format(obsdate[0:4], obsdate[4:6], obsdate[6:8])
    interval = sys.argv[2]

    # use the connection to get the required data: _d
    dr_d = rq.date_range(mysql_con, date, interval=interval)
    wpb_d = rq.weekly_priority_breakdown(mysql_con, date, interval=interval)
    wtb_d = rq.weekly_time_breakdown(mysql_con, date, interval=interval)
    wttb_d = rq.weekly_total_time_breakdown(mysql_con, date, interval=interval)
    wsb_d = rq.weekly_subsystem_breakdown(mysql_con, date, interval=interval)

    # TESTING: save the dataframes
    dr_d.save('dr_d')
    wpb_d.save('wpd_d')
    wtb_d.save('wtb_d')
    wttb_d.save('wttd_d')
    wsb_d.save('wsb_d')


    # format the string needed to print and write to file: _t
    dr_t = string_header(dr_d)
    wpd_t = string_weekly_priority_breakdown(wpb_d)
    wttb_t = string_weekly_total_time_breakdown(wttb_d)
    wsb_t = string_weekly_subsystem_breakdown(wsb_d)

    # print the report to the terminal
    print_to_screen(dr_t + wpd_t + wttb_t + wsb_t)

    # write the report to file
    write_to_file(dr_d, dr_t + wpd_t + wttb_t + wsb_t)

    mysql_con.close()
