"""This program is for recording IMU data, through HC05 bluetooth module"""

import serial
import struct
import keyboard
import csv
from datetime import datetime
import sys
from sys import stdout
import getopt
import time


class SerialPort(object):
    # Contains functions that enable communication between the docking station and the IMU watches

    def __init__(self, serialport, serialrate=9600, csv_path="", csv_enable=False):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()

        self.serialport = serialport
        self.ser_port = serial.Serial(serialport, serialrate)

        self.csv_enabled = csv_enable
        if csv_enable:
            # self.csv_file = open(csv_path + "//imu01.csv", "w")
            self.csv_file = open(csv_path, "w")
            self.csv = csv.writer(self.csv_file)
            self.csv.writerow(["sys_time", "ax", "ay", "az", "gx", "gy", "gz", "imu_time", "imu_rtime"])
        self.triggered = True
        self.connected = False

        stdout.write("Initializing imu program\n")

    def serial_write(self, payload):
        # Format:
        # | 255 | 255 | no. of bytes | payload | checksum |

        header = [255, 255]
        chksum = 254
        payload_size = len(payload) + 1
        chksum += payload_size

        self.ser_port.write(bytes([header[0]]))
        self.ser_port.write(bytes([header[1]]))
        self.ser_port.write(bytes([payload_size]))
        self.ser_port.write(bytes([payload]))
        self.ser_port.write(bytes([chksum % 256]))

    def serial_read(self):
        """returns bool for valid read, also returns the data read"""
        # print(self.ser_port.read())

        if (self.ser_port.read() == b'\xff') and (self.ser_port.read() == b'\xff'):
            self.connected = True
            chksum = 255 + 255
            self.plSz = self.ser_port.read()[0]
            chksum += self.plSz
            self.payload = self.ser_port.read(self.plSz - 1)

            chksum += sum(self.payload)
            chksum = bytes([chksum % 256])
            _chksum = self.ser_port.read()

            # print("inside", self.ser_port.read())

            return _chksum == chksum

        return False

    def disconnect(self):
        stdout.write("disconnected\n")

    def run_program(self):
        for i in range(50000):

            # print("hi there", i)

            if self.serial_read():

                val = struct.unpack("6f", self.payload[0:24])
                time_delta = struct.unpack("Q", self.payload[24:])
                # print(time_delta)

                time_temp = str(time_delta[0]*10)

                dt_time = time_temp[0:4] + "-" + time_temp[4:6] + "-" + time_temp[6:8] + " " + time_temp[8:10] + ":" + time_temp[10:12] + ":"+ time_temp[12:14] + "." + time_temp[14:]
                print(val)
                nw = None

                if not nw:
                    nw = datetime.now()
                    # print(nw)
                if self.csv_enabled:
                    self.csv.writerow([str(nw), val[0], val[1], val[2], val[3], val[4], val[5], dt_time, time_delta[0]])
                if keyboard.is_pressed("e"):

                    self.csv_file.close()
                    break


if __name__ == '__main__':
    # opts, args = getopt.getopt(sys.argv[1:], "p:", ["path"])

    # print(opts[0])
    # _filepath = opts[0][1]

    # myport = SerialPort("COM15", 115200, csv_path=_filepath, csv_enable=True)
    myport = SerialPort("COM4", 115200, csv_path="hc05_rtc_1.csv", csv_enable=True)
    # myport = SerialPort("COM4", 115200)
    myport.run_program()
