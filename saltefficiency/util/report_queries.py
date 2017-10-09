# -*- coding: utf-8 -*-
"""
Created on Thu Mar 12 14:25:11 2015

@author: jpk

This script contains the queries to create the weekly report and the plots.

"""

import pandas as pd
import pandas.io.sql as psql
import matplotlib.pyplot as pl
import numpy as np
from datetime import date


def date_range(mysql_con, date, interval=7):
    '''
    returns the dates for NOW() and 7 days ago. This is used to writing the
    report heading and building the filename
    '''

    dr = pd.read_sql_query('''SELECT DATE_SUB(DATE('{}'), INTERVAL {} DAY) as StartDate,
    DATE_SUB(DATE('{}'), INTERVAL 1 DAY) as  EndDate;
    '''.format(date, interval, date), con=mysql_con)

    return dr


def weekly_priority_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the priority breakdown in terms of no. of blocks
    observed and total time spent per priority for the last week.
    '''

    wpb = pd.read_sql_query('''SELECT Priority, COUNT(*) as "No. Blocks",
    sum(ObsTime) as "Tsec"
    FROM Block
    JOIN BlockVisit USING (Block_Id)
    JOIN BlockVisitStatus USING (BlockVisitStatus_Id)
    JOIN NightInfo USING (NightInfo_Id)
    JOIN Proposal ON (Block.Proposal_Id=Proposal.Proposal_Id)
    JOIN ProposalGeneralInfo ON (Proposal.ProposalCode_Id=ProposalGeneralInfo.ProposalCode_Id)
    JOIN ProposalType USING (ProposalType_Id)
    WHERE Date BETWEEN DATE_SUB(DATE('{}'), INTERVAL {} DAY)
    AND DATE_SUB(DATE('{}'), INTERVAL 1 DAY)
    AND ProposalType.ProposalType NOT IN ('Commissioning', 'Engineering')
    AND BlockVisitStatus.BlockVisitStatus='Accepted' GROUP BY Priority;
    '''.format(date, interval, date), mysql_con)

    return wpb

def lastnight_time_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the time breakdown for last night's observations
    '''

    ltb = pd.read_sql_query('''SELECT Date,
    IFNULL(SUM(TimeLostToWeather), 0) `Weather`,
    IFNULL(SUM(TimeLostToProblems), 0) `Problems`,
    IFNULL(SUM(EngineeringTime), 0) `Engineering`,
    IFNULL(SUM(ScienceTime), 0) `Science`,
    SUM(TIMESTAMPDIFF(SECOND,  EveningTwilightEnd, MorningTwilightStart)) as Total
    FROM NightInfo
    WHERE Date BETWEEN DATE_SUB(DATE(NOW()), INTERVAL 1 DAY) AND DATE_SUB(DATE(NOW()), INTERVAL 1 DAY);

    ''', con=mysql_con, index_col=['Date'])
    ltb.index = pd.to_datetime(ltb.index)

    return ltb

def weekly_time_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the time breakdown for the past week'ss observations
    per night.
    '''
    wtb = pd.read_sql_query('''SELECT Date,
    IFNULL(SEC_TO_TIME(TimeLostToWeather), 0) `TimeLostToWeather`,
    IFNULL(SEC_TO_TIME(TimeLostToProblems), 0) `TimeLostToProblems`,
    IFNULL(SEC_TO_TIME(EngineeringTime), 0) `EngineeringTime`,
    IFNULL(SEC_TO_TIME(ScienceTime), 0) `ScienceTime`,
    SEC_TO_TIME(TIMESTAMPDIFF(SECOND,  EveningTwilightEnd, MorningTwilightStart)) as NightLength,
    IFNULL(TimeLostToWeather / 3600, 0) `Weather`,
    IFNULL(TimeLostToProblems/ 3600, 0) `Problems`,
    IFNULL(EngineeringTime / 3600, 0) `Engineering`,
    IFNULL(ScienceTime / 3600, 0) `Science`,
    TIMESTAMPDIFF(SECOND,  EveningTwilightEnd, MorningTwilightStart) as Night
    FROM NightInfo
    WHERE Date BETWEEN DATE_SUB(DATE('{}'), INTERVAL {} DAY)
    AND DATE_SUB(DATE('{}'), INTERVAL 1 DAY);
    '''.format(date, interval, date), con=mysql_con)

    return wtb


def weekly_total_time_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the total time breakdown for the past week's
    observations.
    '''

    wttb = pd.read_sql_query('''SELECT DATE_SUB(DATE(NOW()), INTERVAL 7 DAY) as StartDate,
    DATE_SUB(DATE(NOW()), INTERVAL 1 DAY) as  EndDate,
    IFNULL(SUM(TimeLostToWeather), 0) `Weather`,
    IFNULL(SUM(TimeLostToProblems), 0) `Problems`,
    IFNULL(SUM(EngineeringTime), 0) `Engineering`,
    IFNULL(SUM(ScienceTime), 0) `Science`,
    SUM(TIMESTAMPDIFF(SECOND,  EveningTwilightEnd, MorningTwilightStart)) as Total
    FROM NightInfo
    WHERE Date BETWEEN DATE_SUB(DATE('{}'), INTERVAL {} DAY)
    AND DATE_SUB(DATE('{}'), INTERVAL 1 DAY);
    '''.format(date, interval, date), con=mysql_con)

    return wttb

def lastnight_subsystem_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the subsystem time breakdown for problems last night
    '''

    lsb = pd.read_sql_query('''SELECT SaltSubsystem,
    SEC_TO_TIME(SUM(TimeLost)) as "TimeLost",
    SUM(TimeLost) as "Time"
    FROM Fault JOIN NightInfo USING (NightInfo_Id) JOIN SaltSubsystem USING (SaltSubsystem_Id)
    WHERE Fault.Deleted=0 AND Timelost IS NOT NULL AND DATE(Date) =  DATE_SUB(DATE('{}'), INTERVAL 1 DAY)
    GROUP BY SaltSubsystem;
    '''.format(date), con=mysql_con)

    return lsb



def weekly_subsystem_breakdown(mysql_con, date, interval=7):
    '''
    this function returns the total time breakdown for problems experienced
    during the past week's observations.
    '''


    wsb = pd.read_sql_query('''SELECT SaltSubsystem,
    SUM(TimeLost) as "Time"
    FROM Fault JOIN NightInfo USING (NightInfo_Id)
    JOIN SaltSubsystem USING (SaltSubsystem_Id)
    WHERE Fault.Deleted=0 AND Timelost IS NOT NULL
    AND Date BETWEEN DATE_SUB(DATE('{}'), INTERVAL {} DAY)
    AND DATE_SUB(DATE('{}'), INTERVAL 1 DAY) GROUP BY SaltSubsystem;
    '''.format(date, interval, date), con=mysql_con)

    return wsb

def weekly_subsystem_breakdown_total(mysql_con, date, interval=7):
    '''
    this function returns the total time breakdown for problems experienced
    during the past week's observations.
    '''

    wsbt = pd.read_sql_query('''SELECT SaltSubsystem,
    SUM(TimeLost) as "Time"
    FROM Fault JOIN NightInfo USING (NightInfo_Id)
    JOIN SaltSubsystem USING (SaltSubsystem_Id)
    WHERE Fault.Deleted = 0 AND Timelost IS NOT NULL
    AND Date BETWEEN DATE_SUB(DATE('{}'), INTERVAL {} DAY)
    AND DATE_SUB(DATE('{}'), INTERVAL 1 DAY);
    '''.format(date, interval, date), con=mysql_con)

    return wsbt

