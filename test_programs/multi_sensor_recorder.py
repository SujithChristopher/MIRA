""" 

this program records video from two cameras simultaneously and saves the
files locally, in message pack format

this is designed to run in Kinect and Realsense

This also records IMU, and data from mecanum wheels, and saves in respective directory

This code is written by Sujith, 13-09-2022
"""

import os
import sys
import time
import datetime
import msgpack as mp
import msgpack_numpy as mpn
import numpy as np
import pyrealsense2 as rs
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime
import cv2
import matplotlib.pyplot as plt
import fpstimer
import multiprocessing
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from imu_services.mecanum_wheel.encoder_stream_test import SerialPort


kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color)

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 1280, 720, rs.format.BW, 15)
pipeline.start(config)

class DualCameraRecorder:
    def __init__(self, _pth):

        """kinect parameters for recording"""
        self.yRes = 736
        self.xRes = 864

        self.xPos = 0
        self.yPos = 0

        self.fps_val = 15
        self._pth = _pth
    
    def kinect_capture_frame(self):
        """kinect capture frame"""
        # kinect capture frame
        
        while True:
            if kinect.has_new_color_frame():
                frame = kinect.get_last_color_frame()
                frame = frame.reshape((1080, 1920, 4))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
                frame = frame[self.yPos * 2:self.yPos * 2 + self.yRes, self.xPos * 2:self.xPos * 2 + self.xRes].copy()
                fpstimer.FPSTimer(self.fps_val)

    def rs_capture_frame(self):

        """capture frame from realsense"""

        # realsense capture frame
        
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            color_image = np.asanyarray(color_frame.get_data())

            if not color_frame:
                continue

                
    def record_for_calibration(self):
        """
        record data for calibration
        this does not include imu and mecanum wheel data
        """
        # record for calibration

    def run(self, cart_sensors):
        """run the program"""
        # run the program

        if not cart_sensors:
            kinect_capture_frame = multiprocessing.Process(target=self.kinect_capture_frame)
            rs_capture_frame = multiprocessing.Process(target=self.rs_capture_frame)

            kinect_capture_frame.start()
            rs_capture_frame.start()

            kinect_capture_frame.join()
            rs_capture_frame.join()

        if cart_sensors:

            myport = SerialPort("COM4", 115200, csv_path=self._pth, csv_enable=True)

            kinect_capture_frame = multiprocessing.Process(target=self.kinect_capture_frame)
            rs_capture_frame = multiprocessing.Process(target=self.rs_capture_frame)
            cart_sensors = multiprocessing.Process(target=myport.run_program)

            kinect_capture_frame.start()
            rs_capture_frame.start()
            cart_sensors.start()

            kinect_capture_frame.join()
            rs_capture_frame.join()
            cart_sensors.join()

if __name__ == "__main__":
    # main program

    _pth = os.path.join(os.path.dirname(__file__), 'test_data')
    if not os.path.exists(_pth):
        os.makedirs(_pth)

    recorder = DualCameraRecorder(_pth)
    recorder.run(cart_sensors=True)

            

        

    