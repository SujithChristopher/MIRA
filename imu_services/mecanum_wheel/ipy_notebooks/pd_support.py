"""this code is written by Sujith"""

import enum
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def read_df_csv(filename, offset=2):
    """
    this function reads the csv file from motion capture system
     and makes it into a dataframe and returns only useful information

    filename: input path to csv file from motive
    offset:to ignore the first two columns with time and frames generally

    """

    # offset = 2 #first two columns with frame_no and time

    pth = filename
    raw = pd.read_csv(pth)
    cols_list = raw.columns     # first row which contains capture start time
    inx = [i for i, x in enumerate(cols_list) if x == "Capture Start Time"]
    st_time = cols_list[inx[0] + 1]
    st_time = datetime.strptime(st_time, "%Y-%m-%d %I.%M.%S.%f %p")  # returns datetime object

    mr_inx = pd.read_csv(pth, skiprows=3)
    markers_raw = mr_inx.columns
    marker_offset = offset  # for ignoring time and frame cols
    markers_raw = markers_raw[marker_offset:]
    col_names = []
    for i in range(0, len(markers_raw), 3):
        col_names.append(markers_raw[i].split(":")[1])

    df_headers = ["frame", "seconds"]
    for i in col_names:
        df_headers.append(i + "_x")
        df_headers.append(i + "_y")
        df_headers.append(i + "_z")
    mo_data = pd.read_csv(pth, skiprows=6)
    # mo_data = mo_data.rename(mo_data.columns, df_headers)
    mo_data.columns = df_headers

    return mo_data, st_time


def add_datetime_col(df, _time, _name):

    """
    df:     dataframe
    _time:  the time you want to start your column with
    _name:  name of the column that has time in seconds
    """

    _t = []
    for i in list(df[_name]):
        _t.append(_time + timedelta(0,float(i)))
    df["time"] = _t
    return df
    
def add_datetime_diff(df, _time, _sync, _diff_name, truncate = False):

    """
    df:         dataframe
    _time:      the time you want to start your column with
    _sync:      Name of the column with external sync which turns 1 when your recording 
                your data and 0 when your not
    _diff_name: external time/ other time which you want to find the difference 
                and add them to the _time column to sync clock
    truncate:   truncate will also cut the values after your _sync goes to 0
    """
    _inx = 0
    for inx, i in enumerate(df[_sync]):
        if i == 1:
            _inx = inx
            break

    df = df.loc[_inx:].copy()     # dropping unnecessary rows

    _diff = list(df[_diff_name].diff())
    _sum = 0
    _t = []
    for i in _diff:
        if np.isnan(i):
            i = 0
        _sum = _sum + i
        _t.append(_time + timedelta(0,float(_sum/1000)))

    df["time"] = _t

    if truncate:
        _count = 0
        for count, j in enumerate(df[_sync]):
            if j == 0:
                _count = count
                print(_count)
                break
        if _count is not 0:   
            df = df.loc[:_count].copy()     # dropping unnecessary rows
    
    return df