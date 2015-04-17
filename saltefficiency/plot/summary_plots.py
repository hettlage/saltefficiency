# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 10:06:20 2015

@author: jpk

ToDo:

*automate the subsystems check. A query that checks all the subsystems in
case things change in the future should prevent issues with the pie chart
colours.

* Need to add global variables for the password.
* Need to property parse commandline options

"""

global __version__
__version__ = "1.0"
__date__ = "20 March 2015"
__author__ = "Paul Kotze"
__doc__ = "\nSALT Observing Summary Plots Generator, version " + __version__ + '''

This script uses queries generated by the report_queries.py script and plots
the relevant data in .png format

Usage: python weekly_summary_plots.py [OPTIONS]

OPTIONS are as follows, arguments are compulsory for both long and short forms.
Example formats are shown:

    -h   --help                  Prints this help
    -s   --startdate=20141220    Sets the start date for the query
    -e   --enddate=20150214      Sets the end date for the qeury
    -d   --date=20150215         Sets the date for the query, if this option
                                 is used a start date is not required, but an
                                 interval is required
    -i   --interval=7            Set the interval, in days, to go back in
                                 history for the query
'''
__usage__='''Usage: python weekly_summary_plots.py [OPTIONS]

OPTIONS are as follows, arguments are compulsory for both long and short forms.
Example formats are shown:

    -h   --help                  Prints this help

Specifying a date range:
    -s   --startdate=20141220    Sets the start date for the query
    -e   --enddate=20150214      Sets the end date for the qeury

Specifying a date and a range in days to query in the past:
    -d   --date=20150215         Sets the date for the query, if this option
                                 is used a start date is not required, but an
                                 interval is required
    -i   --interval=7            Set the interval, in days, to go back in
                                 history for the query
'''

import sys
import os
import getopt
import MySQLdb
import matplotlib.pyplot as pl
import saltefficiency.util.report_queries as rq
import numpy as np
import matplotlib.dates as mdates
from datetime import datetime, timedelta


def usage():
    print __usage__
    raise SystemExit(2)


def validate_date(date_text):
    """
    this function validate the dates provided
    """

    try:
        date = datetime.strptime(date_text, '%Y%m%d')
    except ValueError:
        raise ValueError("Incorrect data format, date should be YYYYMMDD")

    return date


def validate_int(number):

    try:
        num = int(number)
    except ValueError:
        raise ValueError('The interval should be an integer')

    return num


def parse_commandline(argv):
    # executes if module is run from the command line

    # check whether a commandline has been specified
    if len(argv)==0:
        usage()
        sys.exit(2)
    else:
        pass

    # read command line options
    try:
        opts,args = getopt.getopt(argv,"hs:e:d:i:",
                ["help","startdate=","enddate=", "date=","interval="])
    except getopt.GetoptError, inst:
        print inst
        print 'Use --help to get a list of options'
        sys.exit(2)

    # initiate the val_flags
    s_val = False
    e_val = False
    d_val = False
    i_val = False

    # parse them to the relevant variables
    for opt, arg in opts:
        if opt in ('--help'):
            usage()
        elif opt in ('-s','--startdate'):
            s_date = validate_date(arg)
            s_val = True
        elif opt in ('-e','--enddate'):
            e_date = validate_date(arg)
            e_val = True
        elif opt in ('-d','--date'):
            d_date = validate_date(arg)
            d_val = True
        elif opt in ('-i','--interval'):
            inter = validate_int(arg)
            i_val = True
        else:
            print 'Unknown option: ' + opt
            usage()

    # check all the flags and inform the user if there are missing values
    if s_val + e_val == 2:

        # check that the end date is after the start date
        date_diff = (e_date - s_date).days

        if date_diff < 0:
            raise ValueError('The start date cannot be later than the end date')
        else:
            date = datetime.strftime(e_date, '%Y-%m-%d')
            interval = date_diff

    # check that a start AND an end date is specified
    elif s_val + e_val == 1:
        if s_val:
            raise ValueError('You have to specify an end date')
        elif e_val:
            raise ValueError('You have to specify a start date')
        else:
            pass
    else:
        pass

    if d_val + i_val == 2:
        date = datetime.strftime(d_date, '%Y-%m-%d')
        interval = inter
    # check that a date AND an interval is specified
    elif d_val + i_val == 1:
        if d_val:
            raise ValueError('You have to specify an interval with a date')
        elif i_val:
            raise ValueError('You have to specify a date with an interval')
    else:
        pass

    return date, interval


class PlotGeneration:
    """Generation of SALT efficiency summary plots.

    This class offers various methods for generating SALT efficiency summary plots. These generally expect a date, a
    number of nights to plot, a plot title, the output file (or file-like object) and, optionally, the plot format and
    resolution. The date is the date when the last night ends.

    You should use this class in a with structure:

    with PlotGeneration() as pg:
        pg.priority_breakdown(plot_date, interval, title, out, format, dpi)

    Methods:
    --------
    priority_breakdown(plot_date, interval, title, out, format, dpi)
       generate a pie chart with the breakdown of priorities
    total_time_breakdown(plot_date, interval, title, out, format, dpi)
       generate a pie chart with the breakdown of times
    subsystem_breakdown(plot_date, interval, title, out, format, dpi)
       generate a pie chart with the breakdown of subsystem problems
    time_breakdown(plot_date, interval, title, out, format, dpi)
       generate a stacked bar plot with the breakdown of times
    disconnect():
       disconnect from the database (only necessary if you don't use a with statement)

    """

    def __init__(self, db, db_user, db_password, db_host, db_port=3306):
        """Initialise the database connection.

        Parameters:
        -----------
        db: string
           name of the database
        db_user: string
           username of the database user
        db_password: string
           password of the database user
        db_host: string
           database host
        db_port: int
           database port (default is 3306)
        """

        self.db_connection = MySQLdb.connect(host=db_host,
                                             port=db_port,
                                             user=db_user,
                                             passwd=db_password,
                                             db=db)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False  # propagate exceptions

    def disconnect(self):
        """Disconnect from the database if a connection is open.

        Rather than calling this method consider using this class in a with statement.

        It is safe to call this method if the connection is closed already; it will just do nothing.
        """

        if self.db_connection.open:
            self.db_connection.close()

    def priority_breakdown(self, plot_date, interval, title, out, format='png', dpi=100):
        """Output a pie chart for the breakdown of priorities.

         The breakdown is aggregated over all nights from the first to last night. The output target for the plot may either
         be specified by a file path or supplied as a file-like object. (Technically, the oputput target can be any object
         accepted by Matplotlib as an output target.)

         The plot title may contain placeholders {first_night} and {last_night}, which will be replaced with the respective
         date in the format yyy-mm-dd, as well as the placeholder {total_blocks}, which will be replaced with the total
         number of blocks.

         Parameters
         ----------
         plot_date : date
            date for which the plot is created; this is the date when the last night ends
         interval: int
            number of nights to plot
         title: string
            plot title
         out : string or file-like object
            output target where the plot is saved to
         format: string
            format of the generated image (the default is 'png')
         dpi: int
            dpi of the generated image (the default is 100)
        """

        fig = pl.figure(facecolor='w', figsize=[6, 6])
        ax = fig.add_subplot(111)
        ax.set_aspect = 1

        # get data from database
        mysql_con = None
        try:
            x = rq.weekly_priority_breakdown(self.db_connection, plot_date, interval)
        finally:
            if mysql_con:
                mysql_con.close()

        temp = list(x['Priority'])
        no_blocks = map(int, list(x['No. Blocks']))
        labels = ['P'+str(temp[i])+' - ' + str(no_blocks[i]) for i in range(0,len(temp))]
        values = list(x['Tsec'])

        # set colours for the priorities
        colours = ['b','c','g','m','r']

        fig = pl.figure(facecolor='w', figsize=[6, 6])
        ax = fig.add_subplot(111)
        ax.set_aspect=1

        ax.pie(values,
               colors=colours,
               pctdistance=0.8,
               radius=0.95,
               autopct='%1.1f%%',
               textprops={'fontsize': 10,
                          'color': 'w'},
               wedgeprops={'edgecolor': 'white'})

        ax.legend(labels=labels, frameon=False, loc=(-0.15,0.7), fontsize=8)

        first_night = plot_date - timedelta(days=interval)
        last_night = plot_date - timedelta(days=1)
        title_txt = title.format(first_night=first_night,
                                 last_night=last_night,
                                 total_blocks=int(x['No. Blocks'].sum()))
        ax.set_title(title_txt, fontsize=12)

        pl.savefig(out, format=format, dpi=dpi)


    def total_time_breakdown(self, plot_date, interval, title, out, format='png', dpi=100):
        """Output a pie chart for the breakdown of time.

         The time is summed up for all nights from the first to last night. The output target for the plot may either
         be specified by a file path or supplied as a file-like object. (Technically, the oputput target can be any object
         accepted by Matplotlib as an output target.)

         The plot title may contain placeholders {first_night} and {last_night}, which will be replaced with the respective
         date in the format yyy-mm-dd, as well as the placeholder {total_night_length}, which will be replaced with the
         total night length in seconds.

         Parameters
         ----------
         plot_date : date
            date for which the plot is created; this is the date when the last night ends
         interval: int
            number of nights to plot
         title: string
            plot title
         out : string or file-like object
            output target where the plot is saved to
         format: string
            format of the generated image (the default is 'png')
         dpi: int
            dpi of the generated image (the default is 100)
        """

        fig = pl.figure(facecolor='w', figsize=[6, 6])
        ax = fig.add_subplot(111)
        ax.set_aspect = 1

        # get data from database
        x = rq.weekly_total_time_breakdown(self.db_connection, plot_date, interval)

        labels = ['Science - {}'.format(x['ScienceTime'][0]),
                  'Engineering - {}'.format(x['EngineeringTime'][0]),
                  'Weather - {}'.format(x['TimeLostToWeather'][0]),
                  'Problems - {}'.format(x['TimeLostToProblems'][0])]

        values = [int(x['Science']),
                  int(x['Engineering']),
                  int(x['Weather']),
                  int(x['Problems'])]

        colours = ['b','c','g','r']

        ax.pie(values,
               colors=colours,
               pctdistance=0.8,
               radius=0.95,
               autopct='%1.1f%%',
               textprops={'fontsize': 10,
                          'color': 'w'},
               wedgeprops={'edgecolor': 'white'})

        ax.legend(labels=labels, frameon=False, loc=(-0.15,0.8), fontsize=8)

        first_night = plot_date - timedelta(days=interval)
        last_night = plot_date - timedelta(days=1)
        title_txt = title.format(first_night=first_night,
                                 last_night=last_night,
                                 total_night_length=x['NightLength'][0])
        ax.set_title(title_txt, fontsize=12)

        pl.savefig(out, format=format, dpi=dpi)


    def subsystem_breakdown(self, plot_date, interval, title, out, format='png', dpi=100):
        """Output a pie chart for the breakdown of time lost due to problems.

         The breakdown is shown for all nights from the first to last night. The output target for the plot may either be
         specified by a file path or supplied as a file-like object. (Technically, the oputput target can be any object
         accepted by Matplotlib as an output target.)

         Note that if you want the breakdown for a single night, you have to pass the same date as the first and last night.

         The plot title may contain placeholders {first_night} and {last_night}, which will be replaced with the respective
         date in the format yyy-mm-dd, as well as the placeholder {total_time}, which will be replaced with the total time
         in seconds.

         Parameters
         ----------
         plot_date : date
            date for which the plot is created; this is the date when the last night ends
         interval: int
            number of nights to plot
         title: string
            plot title
         out : string or file-like object
            output target where the plot is saved to
         format: string
            format of the generated image (the default is 'png')
         dpi: int
            dpi of the generated image (the default is 100)
        """

        fig = pl.figure(facecolor='w', figsize=[6, 6])
        ax = fig.add_subplot(111)
        ax.set_aspect = 0.8

        # set the colours for all the subsystems:
        subsystems_list = ['BMS', 'DOME', 'TC', 'PMAS', 'SCAM', 'TCS', 'STRUCT',
                           'TPC', 'HRS', 'PFIS','Proposal', 'Operations',
                           'ELS', 'ESKOM']
        cmap = pl.cm.jet
        colour_map = cmap(np.linspace(0.0, 1.0, len(subsystems_list)))
        col_dict = {}

        for i in range(0, len(subsystems_list)):
            col_dict[subsystems_list[i]] = colour_map[i]

        # get data from database
        x = rq.weekly_subsystem_breakdown(self.db_connection, plot_date, interval)
        y = rq.weekly_subsystem_breakdown_total(self.db_connection, plot_date, interval)

        subsystem = list(x['SaltSubsystem'])
        time = list(x['TotalTime'])

        labels = [subsystem[i] + ' - ' + time[i] for i in range(0, len(subsystem))]
        values = list(x['Time'])

        colours = [col_dict[i] for i in subsystem]

        ax.pie(values,
               colors=colours,
               pctdistance=0.8,
               radius=0.9,
               autopct='%1.1f%%',
               textprops={'fontsize': 10,
                          'color': 'k'},
               wedgeprops={'edgecolor': 'white'})

        ax.legend(labels=labels, frameon=False, loc=(-0.15,0.5), fontsize=8)

        first_night = plot_date - timedelta(days=interval)
        last_night = plot_date - timedelta(days=1)
        title_txt = title.format(first_night=first_night.strftime('%Y-%m-%d'),
                                 last_night=last_night.strftime('%Y-%m-%d'),
                                 total_time=y['TotalTime'][0])
        ax.set_title(title_txt, fontsize=12)

        pl.savefig(out, format=format, dpi=dpi)


    def time_breakdown(self, plot_date, interval, title, out, format='png', dpi=100):
        """Output a stacked bar plot of the time breakdown.

         The breakdown is shown for all nights from the first to last night. The output target for the plot may either be
         specified by a file path or supplied as a file-like object. (Technically, the oputput target can be any object
         accepted by Matplotlib as an output target.)

         Note that if you want the breakdown for a single night, you have to pass the same date as the first and last night.

         The plot title may contain placeholders {first_night} and {last_night}, which will be replaced with the respective
         date in the format yyy-mm-dd.

         Parameters
         ----------
         plot_date : date
            date for which the plot is created; this is the date when the last night ends
         interval: int
            number of nights to plot
         title: string
            plot title
         out : string or file-like object
            output target where the plot is saved to
         format: string
            format of the generated image (the default is 'png')
         dpi: int
            dpi of the generated image (the default is 100)
        """

        fig = pl.figure(figsize=(10,4), facecolor='w')
        ax = fig.add_subplot(111)
        width = 0.65
        ax.grid(which='major', axis='y')

        # get data from database
        data = rq.weekly_time_breakdown(self.db_connection, plot_date, interval)

        # science time per day
        s = ax.bar(data['Date'],
                   data['Science'],
                   width,
                   color='b',
                   edgecolor='w')

        # engineering time per day
        e = ax.bar(data['Date'],
                   data['Engineering'],
                   width,
                   bottom=data['Science'],
                   color='c',
                   edgecolor='w')

        # weather time per day
        w = ax.bar(data['Date'],
                   data['Weather'],
                   width,
                   bottom=data['Science'] + data['Engineering'],
                   color='g',
                   edgecolor='w')

        # problem time per day
        p = ax.bar(data['Date'],
                   data['Problems'],
                   width,
                   bottom=data['Science'] + data['Engineering'] + data['Weather'],
                   color='r',
                   edgecolor='w')


        ax.set_ylabel('Hours', fontsize=11)
        ax.set_xlabel('Date', fontsize=11)
        fig.legend((s[0], e[0], w[0], p[0]),
                   ('Science Time',
                    'Engineering Time',
                    'Time lost to Weather',
                    'Time lost to Problems'),
                   frameon=False,
                   fontsize=10,
                   loc=(0.0, 0.70))

        first_night = plot_date - timedelta(days=interval)
        last_night = plot_date - timedelta(days=1)
        title_txt = title.format(first_night=first_night.strftime('%Y-%m-%d'),
                                 last_night=last_night.strftime('%Y-%m-%d'))

        ax.set_title(title_txt, fontsize=11)
        ax.xaxis_date()
        date_formatter = mdates.DateFormatter('%a \n %Y-%m-%d')
        ax.xaxis.set_major_formatter(date_formatter)

        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(8)
        for tick in ax.yaxis.get_major_ticks():
            tick.label.set_fontsize(8)

        fig.autofmt_xdate(rotation=0, ha='left')
        fig.subplots_adjust(left=0.22, bottom=0.20, right=0.96, top=None,
                            wspace=None, hspace=None)
        pl.autoscale()
        pl.savefig(out, format=format, dpi=dpi)


if __name__ == '__main__':
    def generate_plots():
         # open mysql connection to the sdb
        mysql_con = MySQLdb.connect(host='devsdb',
                                    port=3306,
                                    user=os.environ['SDBUSER'],
                                    passwd=os.environ['SDBPASS'],
                                    db='sdb_v6')

    #    obsdate = sys.argv[1]
    #    date = '{}-{}-{}'.format(obsdate[0:4], obsdate[4:6], obsdate[6:8])
    #    interval = sys.argv[2]

        date, my_interval = parse_commandline(sys.argv[1:])

        plotdate = datetime.strptime(date, '%Y-%m-%d').date()
        first_night = plotdate - timedelta(days=my_interval)
        last_night = plotdate - timedelta(days=1)
        first_night_txt = first_night.strftime('%Y%m%d')
        last_night_txt = last_night.strftime('%Y%m%d')

        # testing the pie_chart method
        with PlotGeneration(db='sdb_v6',
                            db_user=os.environ['SDBUSER'],
                            db_password=os.environ['SDBPASS'],
                            db_host='devsdb') as pg:
             pg.priority_breakdown(plot_date=plotdate,
                                      interval=my_interval,
                                      title='Weekly Priority Breakdown - {total_blocks} Blocks Total' + '\n {first_night} - {last_night}',
                                      out=file('priority_breakdown_pie_chart_{}-{}.png'.format(first_night_txt, last_night_txt), mode='w'))
             pg.total_time_breakdown(plot_date=plotdate,
                                        interval=my_interval,
                                        title='Weekly Time Breakdown - {total_night_length} Total\n{first_night} - {last_night}',
                                        out=file('total_time_breakdown_pie_chart_{}-{}.png'.format(first_night_txt, last_night_txt), mode='w'))
             pg.subsystem_breakdown(plot_date=plotdate,
                                    interval=my_interval,
                                    title='Weekly Problems Breakdown - {total_time}\n{first_night} - {last_night}',
                                    out=file('subsystem_breakdown_pie_chart_{}-{}.png'.format(first_night_txt, last_night_txt), mode='w'))
             pg.time_breakdown(plot_date=plotdate,
                               interval=my_interval,
                               title='Weekly Time Breakdown - {first_night} - {last_night}',
                               out=file('time_breakdown_{}-{}.png'.format(first_night_txt, last_night_txt), mode='w'))

    generate_plots()