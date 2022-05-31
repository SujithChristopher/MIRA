# -*- coding: utf-8 -*-
"""
A simple program to read IMU data at 100Hz from the Arduino Nano 33 IOT board.
"""

import asyncio
from multiprocessing import ProcessError
import struct
import sys
from typing import Dict
import calendar
from datetime import datetime
import pandas as pd
import numpy as np
from importlib_metadata import csv
import keyboard
import matplotlib.pyplot as plt
import time

import bleak
from bleak import BleakClient
from bleak import discover

# These values have been randomly generated - they must match between the Central and Peripheral devices
# Any changes you make here must be suitably made in the Arduino program as well
IMU_UUID = '13012F01-F8C3-4F4A-A8F4-15CD926DA146'
COM_UUID = '7B85CD52-6F02-4933-816C-375FB8091A2D'

# Commands defined on the IMU watch
PING = 1
LISTFILES = 2
SENDFILE = 3
DELETEFILE = 4
TERMINATE = 5
SETTIME = 6
STREAMDATA = 7
STOPSTREAM = 8


# Class for handling BLE communication for receiving IMU data.
class IMUBLEClient(object):

    def __init__(self, uuid: str, csvout: bool = True) -> None:
        super().__init__()
        self._client = None
        self._device = None
        self._connected = False
        self._running = False
        self._uuid = uuid
        self._found = False
        self.packetsize = 22
        self.payloadsize = 10
        self.start = datetime.now()
        self.sample = 0
        self.freq = 0
        self.newdata = False
        self._data = {"time": 0.0,
                      "ax": 0, "ay": 0, "az": 0,
                      "gx": 0, "gy": 0, "gz": 0, "sample": 0}
        with open("C:/Dummy_ble/data_imu2.csv", 'w') as csvfile:
            csvfile.write("time,ax_1,ay_1,az_1,gx_1,gy_1,gz_1\n")
        self._csvout = True
        self.newdata = False
        self.printdata = True
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
        print('Looking for Peripheral Device...')
        devices = await discover()
        print([d.name for d in devices])
        for d in devices:
            if 'imu2' in d.name:
                self._found = True
                self._device = d
                print(d)
                sys.stdout.write(f'Found Peripheral Device {self._device.name}. ')
                # await self._device.pair()
                break

        async with BleakClient(d.address) as self._client:
            sys.stdout.write(f'Connected.\n')
            self._connected = True
            await self.set_time()
            await self.start_stream()
            self.start = datetime.now()
            while self._connected:
                if self._running:
                    await asyncio.sleep(0)

    async def disconnect(self) -> None:
        if self._connected:
            # Stop notification first.
            self._client.stop_notify()
            self._client.disconnect()
            self._connected = False
            self._running = False

    async def ping(self):
        await self._client.write_gatt_char(COM_UUID, bytes([PING]))
        timestamp = get_timestamp(await self._client.read_gatt_char(COM_UUID))
        return timestamp

    async def set_time(self):
        delay = []
        for i in range(10):
            dt = datetime.now()
            unix = f'{int(dt.microsecond / 10000)},{dt.second},{dt.minute},{dt.hour},{dt.day},{dt.month},{dt.year % 100}'
            await self._client.write_gatt_char(COM_UUID, bytes([SETTIME]) + bytearray(unix.encode()))
            timestamp = get_timestamp(await self._client.read_gatt_char(COM_UUID))
            currdelay = (datetime.now() - timestamp).total_seconds() * 1000
            delay.append(currdelay)

        delayms = np.mean(delay)
        print(f'average delay = {delayms}')

    async def start_stream(self) -> None:
        await self._client.write_gatt_char(COM_UUID, bytes([STREAMDATA]))
        if self._connected:
            # Start notification
            await self._client.start_notify(IMU_UUID, self.newdata_hndlr)
            self._running = True

    def newdata_hndlr(self, sender, data):
        for i in range(self.payloadsize):
            elapsed = (datetime.now() - self.start).total_seconds()
            self._data['time'] = struct.unpack('<d', bytes(data[(i*self.packetsize) + 0:(i*self.packetsize) + 8]))[-1]
            self._data['ax'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 8:(i*self.packetsize) + 10]))[-1]
            self._data['ay'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 10:(i*self.packetsize) + 12]))[-1]
            self._data['az'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 12:(i*self.packetsize) + 14]))[-1]
            self._data['gx'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 14:(i*self.packetsize) + 16]))[-1]
            self._data['gy'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 16:(i*self.packetsize) + 18]))[-1]
            self._data['gz'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 18:(i*self.packetsize) + 20]))[-1]
            self._data['sample'] = struct.unpack('<h', bytes(data[(i*self.packetsize) + 20:(i*self.packetsize) + 22]))[-1]
            # print(self._data)
            self.print_newdata()
            if elapsed > 1:
                self.freq = self.sample
                self.sample = 0
                self.start = datetime.now()
            self.sample = self.sample + 1

    def print_newdata(self) -> None:

        _str = (f"{time.time()}, " +
                f"{self.data['time']:3.3f}, " +
                # f"{self.data['packetnum']:3.0f}, " +
                # f"{self.data['mils']:3.0f}, " +
                f"{self.data['ax']:+1.3f}, " +
                f"{self.data['ay']:+1.3f}, " +
                f"{self.data['az']:+1.3f}, " +
                f"{self.data['gx']:+3.3f}, " +
                f"{self.data['gy']:+3.3f}, " +
                f"{self.data['gz']:+3.3f}, " +
                f"{self.data['sample']}\n")
        with open("C:/Dummy_ble/data_imu2.csv", 'a') as csvfile:
            csvfile.write(_str)

        _str = (f"\r Time: {self.data['time']:3.3f} | " +
                # f"Packet Num: {self.data['packetnum']:3.0f} | " +
                # f"Mils: {self.data['mils']:3.0f} | " +
                "Accl: " +
                f"{(self.data['ax']) / 16384:+1.3f}, " +
                f"{(self.data['ay']) / 16384:+1.3f}, " +
                f"{(self.data['az']) / 16384:+1.3f} | " +
                "Gyro: " +
                f"{self.data['gx']:+3.3f}, " +
                f"{self.data['gy']:+3.3f}, " +
                f"{self.data['gz']:+3.3f} | " +
                f"Freq: {self.freq}")
        sys.stdout.write(_str)
        sys.stdout.flush()

    async def stop_stream(self) -> None:
        if self._running:
            # Stop notification
            # await self._client.stop_notify(IMU_UUID)
            await self._client.write_gatt_char(COM_UUID, bytes([STOPSTREAM]))


async def run():
    # Create a new IMU client.
    imu_client = IMUBLEClient(IMU_UUID, False)
    await imu_client.connect()


def get_timestamp(received_bytes):
    ts = [struct.unpack('<L', received_bytes[4 * i:4 * (i + 1)])[-1] for i in range(7)]
    timestring = f'{ts[0]}-{ts[1]}-{ts[2]}T{ts[3]}:{ts[4]}:{ts[5]}.{ts[6]}'
    return datetime.strptime(timestring, '%y-%m-%dT%H:%M:%S.%f')


if __name__ == "__main__":
    # dataformat = np.dtype({'names': ('time', 'ax', 'ay', 'az', 'gx', 'gy', 'gz'),
    #                        'formats': ('f8', 'i2', 'i2', 'i2', 'i2', 'i2', 'i2')})
    # dat = pd.DataFrame(np.fromfile("E:/log97.txt", dataformat))
    # # freq = dat.groupby('time').count()['mils'].values
    # dat['time'] = pd.to_datetime(dat['time'], unit='s')
    # print(dat)
    # dat.to_csv('D:/arm use/nano ble/sddata.csv')
    # print(freq.mean())
    # First create an object
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print('\nReceived Keyboard Interrupt')
    finally:
        print('Program finished')
