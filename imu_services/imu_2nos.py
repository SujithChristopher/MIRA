# -*- coding: utf-8 -*-
"""
A simple program to read IMU data at 100Hz from the Arduino Nano 33 IOT board.
"""

import asyncio
from multiprocessing import ProcessError
import struct
import sys
from typing import Dict
from importlib_metadata import csv
import keyboard

import bleak
from bleak import BleakClient
from bleak import discover
import threading
from datetime import datetime
import getopt
# These values have been randomly generated - they must match between the Central and Peripheral devices
# Any changes you make here must be suitably made in the Arduino program as well
L_IMU_UUID = '13012F01-F8C3-4F4A-A8F4-15CD926DA146'
R_IMU_UUID = '13012F05-F8C3-4F4A-A8F4-15CD926DA146'

# Class for handling BLE communication with a Nano board for receiving IMU data.
class NanoIMUBLEClient(object):
    
    def __init__(self, uuid:str, device_no:int, csvout:bool=True, csvpth="",trigger:bool = True) -> None:
        super().__init__()
        self._client = None
        self._device = None
        self._connected = False
        self._running = False
        self._uuid = uuid
        self._found = False
        self._data = {"time": 0, 
                      "ax": 0.0, "ay": 0.0, "az": 0.0,
                      "gx": 0.0, "gy": 0.0, "gz": 0.0}
        self._csvout = csvout 
        self.newdata = False
        self.printdata = True
        self._imu = device_no
        self._trigger = trigger
        self._csvpath = csvpth+"//"+str(device_no)+"_imu.csv"
        print(self._csvpath)
        
        if self._csvout and self._csvpath:
            self._csv_file = open(self._csvpath, 'w')
            self._csv = csv.writer(self._csv_file)
            self._csv.writerow(["sys_time","imu_time","ax", "ay", "az", "gx", "gy", "gz"])
            
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    @property
    def data(self) -> Dict:
        return self._data

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def running(self) -> bool:
        return self._running
    
    @property
    def device(self):
        return self._device
    
    async def connect(self) -> None:
        if self._connected:
            return
        
        # Currently not connected.
        print('Arduino Nano IMU Service')
        print('Looking for Peripheral Device...')
        devices = await discover()
        for d in devices:
            if self._imu == 1:
                if 'BLE IMU LEFT'in d.name:
                    self._found = True
                    self._device = d
                    sys.stdout.write(f'Found Peripheral Device {self._device.address}. ')
                    break
            if self._imu == 2:
                if 'BLE IMU RIGHT'in d.name:
                    self._found = True
                    self._device = d
                    sys.stdout.write(f'Found Peripheral Device {self._device.address}. ')
                    break
        
        # Connect and do stuff.
        async with BleakClient(d.address) as self._client:
            sys.stdout.write(f'Connected.\n')
            self._connected = True
            # Start getting data.
            await self.start()
            # Run while connected.
            while self._connected:
                if self._running:
                    # Print data.
                    if self.printdata and self.newdata:
                        self.print_newdata()
                        self.newdata = False
                    await asyncio.sleep(0)
    
    async def disconnect(self) -> None:
        if self._connected:
            # Stop notification first.
            self._client.stop_notify()
            self._client.disconnect()
            self._connected = False
            self._running = False
    
    async def start(self) -> None:
        if self._connected:
            # Start notification
            await self._client.start_notify(self._uuid, self.newdata_hndlr)
            self._running = True
    
    async def stop(self) -> None:
        if self._running:
            # Stop notification
            await self._client.stop_notify(self._uuid)
        
    def newdata_hndlr(self, sender, data):
        self._data['time'] = struct.unpack('<L', bytes(data[0:4]))[-1]
        self._data['ax'] = struct.unpack('<f', bytes(data[4:8]))[-1]
        self._data['ay'] = struct.unpack('<f', bytes(data[8:12]))[-1]
        self._data['az'] = struct.unpack('<f', bytes(data[12:16]))[-1]
        self._data['gx'] = struct.unpack('<f', bytes(data[16:20]))[-1]
        self._data['gy'] = struct.unpack('<f', bytes(data[20:24]))[-1]
        self._data['gz'] = struct.unpack('<f', bytes(data[24:28]))[-1]
        self.newdata = True
    
    def print_newdata(self) -> None:
        if self._csvout:
            nw = datetime.now()
            _str = (f"{str(nw)}, " +
                    f"{self.data['time']/1000000.0:+3.3f}, " +
                    
                    f"{self.data['ax']:+1.3f}, " + 
                    f"{self.data['ay']:+1.3f}, " + 
                    f"{self.data['az']:+1.3f}, " +
                    f"{self.data['gx']:+3.3f}, " +
                    f"{self.data['gy']:+3.3f}, " +
                    f"{self.data['gz']:+3.3f}\n")
            nw = datetime.now()
            self._csv.writerow([str(nw), self.data["time"]/1000000, self.data['ax'], self.data['ay'], self.data['az'] , self.data['gx'] , self.data['gy'] , self.data['gz']])
        else:
            _str = (f"\r Time: {self.data['time']/1000000.0:+3.3f} | " +
                    "Accl: " +
                    f"{self.data['ax']:+1.3f}, " + 
                    f"{self.data['ay']:+1.3f}, " + 
                    f"{self.data['az']:+1.3f} | " +
                    "Gyro: " +
                    f"{self.data['gx']:+3.3f}, " +
                    f"{self.data['gy']:+3.3f}, " +
                    f"{self.data['gz']:+3.3f}")
        # sys.stdout.write(_str)
        # sys.stdout.flush()


async def run_imu_left(filepath):
            
    imu_client_left = NanoIMUBLEClient(L_IMU_UUID, device_no = 1, csvpth=filepath)
    await imu_client_left.connect()

#intermediate callback to execure async funciton    
def between_callback_left(filepath):
    print(*args)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(run_imu_left(filepath))
    loop.close()
    
async def run_imu_right(filepath):
    # Create a new IMU client.
    
    imu_client_right = NanoIMUBLEClient(R_IMU_UUID, device_no = 2, csvpth=filepath)
    await imu_client_right.connect()

#intermediate callback to execure async funciton    
def between_callback_right(filepath):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(run_imu_right(filepath))
    loop.close()

def start_imu_service():        
    t1 = threading.Thread(target=between_callback_left)
    t2 = threading.Thread(target=between_callback_right)
  
    # starting thread 1
    t1.start()
    # starting thread 2
    t2.start()
  
    # wait until thread 1 is completely executed
    t1.join()
    # wait until thread 2 is completely executed
    t2.join()

if __name__ == "__main__":
    # First create an object
    
    opts, args = getopt.getopt(sys.argv[1:], "p:", ["path"])

    print(opts[0])
    _filepath = opts[0][1]
            
    t1 = threading.Thread(target=between_callback_left, args=(_filepath,))
    t2 = threading.Thread(target=between_callback_right, args=(_filepath,))
  
    # starting thread 1
    t1.start()
    # starting thread 2
    t2.start()
  
    # wait until thread 1 is completely executed
    t1.join()
    # wait until thread 2 is completely executed
    t2.join()
