
"""Tools and queries for the sdb
"""
import numpy as np
import struct
import datetime
import time

def getnightinfo(sdb, obsdate):
    """Get the NightInfo_Id for an observing date

    Parameters
    ----------
    sdb: ~mysql.mysql
       A connection to the sdb database

    obsdate: str
       Observing date in YYYYMMDD format

    """

    return sdb.select('NightInfo_Id', 'NightInfo', 'Date=%s' % obsdate)[0][0]

def get_weather_info(els, stime, etime):
   """Get the weather status from the start time to the endtime"""

   #convert times to ELS time format
   stime=time.mktime(stime.timetuple())+2082852000-7200
   etime=time.mktime(etime.timetuple())+2082852000-7200

   #now extact weather information from the els
   sel_cmd='timestamp, air_pressure, dewpoint, rel_humidity, wind_mag_30m, wind_dir_30m, wind_mag_10m, wind_dir_10m, temperatures, rain_detected'
   tab_cmd='bms_external_conditions'
   log_cmd="timestamp>%i and timestamp<%i" % (stime, etime)
   wea_rec=els.select(sel_cmd, tab_cmd, log_cmd)

   time_list=np.zeros(len(wea_rec))
   air_arr=np.zeros(len(wea_rec))
   dew_arr=np.zeros(len(wea_rec))
   hum_arr=np.zeros(len(wea_rec))
   w30_arr=np.zeros(len(wea_rec))
   w30d_arr=np.zeros(len(wea_rec))
   w10_arr=np.zeros(len(wea_rec))
   w10d_arr=np.zeros(len(wea_rec))
   rain_list=[]
   t02_arr=np.zeros(len(wea_rec))
   t05_arr=np.zeros(len(wea_rec))
   t10_arr=np.zeros(len(wea_rec))
   t15_arr=np.zeros(len(wea_rec))
   t20_arr=np.zeros(len(wea_rec))
   t25_arr=np.zeros(len(wea_rec))
   t30_arr=np.zeros(len(wea_rec))

   for i in range(len(wea_rec)):
       time_list[i]=wea_rec[i][0]-stime
       air_arr[i]=wea_rec[i][1]
       dew_arr[i]=wea_rec[i][2]
       hum_arr[i]=wea_rec[i][3]
       w30_arr[i]=wea_rec[i][4]
       w30d_arr[i]=wea_rec[i][5]
       w10_arr[i]=wea_rec[i][6]
       w10d_arr[i]=wea_rec[i][7]
       rain_list.append(wea_rec[i][9])
       t_arr=converttemperature(wea_rec[i][8])
       t02_arr[i]=t_arr[0]
       t05_arr[i]=t_arr[1]
       t10_arr[i]=t_arr[2]
       t15_arr[i]=t_arr[3]
       t20_arr[i]=t_arr[4]
       t25_arr[i]=t_arr[5]
       t30_arr[i]=t_arr[6]

   return time_list, air_arr, dew_arr, hum_arr, w30_arr, w30d_arr, w10_arr, \
          w10d_arr, rain_list, t02_arr, t05_arr, t10_arr, t15_arr, t20_arr, \
          t25_arr, t30_arr

def converttemperature(tstruct, nelements=7):
    t_arr=np.zeros(nelements)
    for i in range(nelements):
        t_arr[i]=float(struct.unpack('>d', tstruct[4+8*i:4+8*(i+1)])[0])
    return t_arr

