
from numpy.core.defchararray import array
import serial
import struct
import numpy as np
import matplotlib.pyplot as plt
import keyboard
import csv
from datetime import datetime



class SerialPort(object):
    # Contains functions that enable communication between the docking station and the IMU watches


    def __init__(self, serialport, serialrate=9600):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()

        self.serialport = serialport
        self.ser = serial.Serial(serialport, serialrate)
        self.csv_file = open("hc05_transmission.csv", "w")
        self.csv = csv.writer(self.csv_file)
        self.csv.writerow(["sys_time", "ax", "ay", "ax", "gx", "gy", "gz"])

        
    def serial_write(self, payload):
        # Format:
        # | 255 | 255 | no. of bytes | payload | checksum |

        header = [255, 255]
        chksum = 254

        payload_size = len(payload) + 1

        chksum += payload_size 

        self.ser.write(bytes([header[0]]))
        self.ser.write(bytes([header[1]]))
        self.ser.write(bytes([payload_size]))

        self.ser.write(bytes([payload]))

        
        self.ser.write(bytes([chksum % 256]))

    def serial_read(self):
        
       
        if (self.ser.read() == b'\xff') and (self.ser.read() == b'\xff'):
            
            self.count += 1
            
            print(self.count)
            chksum = 255 + 255

            self.plSz = self.ser.read()[0]
            
            chksum += self.plSz

            self.payload = self.ser.read(self.plSz - 1)
           
            chksum += sum(self.payload)
            chksum = bytes([chksum % 256])
            _chksum = self.ser.read()

            return _chksum == chksum
        return False
    
    def myfun(self):
        while 1:
            if self.serial_read():
                val = struct.unpack("6f", self.payload)
                nw = datetime.now()
                self.csv.writerow([str(nw), val[0], val[1], val[2], val[3], val[4], val[5]])
                if keyboard.is_pressed("e"):
                    self.csv_file.close()
                    break
                

                # print(val)
            
    


myport = SerialPort("COM15", 115200)
myport.myfun()
