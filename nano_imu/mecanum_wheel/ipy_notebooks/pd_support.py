"""this code is written by Sujith"""

import pandas as pd
from datetime import datetime


def read_df_csv(filename, offset=2):
    """
    this function reads the csv file from motion capture system
     and makes it into a dataframe and returns only useful information

    filename: input path to csv file from motive
    offset:to ignore the first two columns with time and frames generally

    """

    # marker_no = 3 #number of markers in tracking data
    # offset = 2 #first two columns with frame_no and time

    pth = filename
    raw = pd.read_csv(pth)
    cols_list = raw.columns
    inx = [i for i, x in enumerate(cols_list) if x == "Capture Start Time"]  # => [1, 3]
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
