from PyQt5 import QtWidgets
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *

from numpy.core.defchararray import array
import serial
import pandas as pd
import time
import struct
import numpy as np
import matplotlib.pyplot as plt
import keyboard
import csv
from datetime import datetime
from threading import Thread
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal,pyqtSlot




class SerialPort(object):
    # Contains functions that enable communication between the docking station and the IMU watches
    data= pyqtSignal(list)
    progress_callback = pyqtSignal(list)

    def __init__(self, serialport, serialrate=9600):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()
        self.sw=0
        self.sw1=True
        self.dummy=0
        self.Ax=[]
        self.Ay=[]
        self.Az=[]
        self.Gx=[]
        self.Gy=[]
        self.Gz=[]
        self.Ax1=[]
        self.Ay1=[]
        self.Az1=[]
        self.Gx1=[]
        self.Gy1=[]
        self.Gz1=[]

        # Initialise serial port
        running = False
        self.serialport = serialport
        self.ser = serial.Serial(serialport, serialrate)

        self.mydata = pd.DataFrame(columns=["ax", "ay", "az", "cx", "cy", "cz","ax1", "ay1", "az1", "cx1", "cy1", "cz1"])
        
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
    
    # def recordData(self,header,filename=' '):
    #     #keyboard.wait('enter')
       
    #     with open(filename, 'w', encoding='UTF8', newline='') as f:
    #         writer = csv.writer(f)
    #         writer.writerow(header)
    #         current_date_time = datetime.now()
    #         while True:
    #             try: 
    #                 # if myapp.Mainwindow.stop_record.is_killed == True:  
    #                 if not self.sw:
    #                     print('Recording stopped!')
    #                     break  
    #             except:
    #                 break  
    #             #if self.serial_read():
    #             print(len(self.payload))
    #             y1=list(struct.unpack('12f',self.payload))
                
                
    #             y1.insert(0, current_date_time)
    #             #print(len(y1))   
    #             writer.writerow(y1)

    def show_data(self):
        
        self.Ax=[]
        self.Ay=[]
        self.Az=[]
        self.Gx=[]
        self.Gy=[]
        self.Gz=[]
        self.Ax1=[]
        self.Ay1=[]
        self.Az1=[]
        self.Gx1=[]
        self.Gy1=[]
        self.Gz1=[]
        chksum=0
        _chksum=1
        payload=[]
        y1=[]
        x=[]
        while True: 
            trl=self.ser.read(10)
            x.append(trl)
            x=np.array(x)
            x.flatten()
            if x[0]==b'\xff' and x[1]==b'\xff':
                self.count += 1
            
                print(self.count)
                self.chksum = 255 + 255

                self.plSz = struct.unpack('1b',x[2])
            
                self.chksum += self.plSz

                payload = x[3:4]
           
                chksum += sum(payload)
                chksum = bytes([chksum % 256])
                _chksum = x[5]
                x=x[-5:]
            else:
                x=x[-0:]

            
                if chksum==_chksum:
                    print('yes')
                    y=list(struct.unpack('1h',self.payload))
                    if self.sw:
                        self.dummy=1
                        y[0]=float(y[0])/131.0
                        # y[1]=float(y[1])/131.0
                        # y[2]=float(y[2])/131.0
                        # y[3]=float(y[3])/16384.0
                        # y[4]=float(y[4])/16384.0
                        # y[5]=float(y[5])/16384.0
                        # y[6]=float(y[6])/131.0
                        # y[7]=float(y[7])/131.0
                        # y[8]=float(y[8])/131.0
                        # y[9]=float(y[9])/16384.0
                        # y[10]=float(y[10])/16384.0
                        # y[11]=float(y[11])/16384.0
                        # y[12]=float(y[12])/131.0
                        # y[13]=float(y[13])/131.0
                        # y[14]=float(y[14])/131.0
                        # y[15]=float(y[15])/16384.0
                        # y[16]=float(y[16])/16384.0
                        # y[17]=float(y[17])/16384.0
                        # y[18]=float(y[18])/131.0
                        # y[19]=float(y[19])/131.0
                        # y[20]=float(y[20])/131.0
                        # y[21]=float(y[21])/16384.0
                        # y[22]=float(y[22])/16384.0
                        # y[23]=float(y[23])/16384.0

                        # y[24]=float(y[24])/131.0
                        # y[25]=float(y[25])/131.0
                        # y[26]=float(y[26])/131.0
                        # y[27]=float(y[27])/16384.0
                        # y[28]=float(y[28])/16384.0
                        # y[29]=float(y[29])/16384.0
                    # y[30]=float(y[30])/131.0
                    # y[31]=float(y[31])/131.0
                    # y[32]=float(y[32])/131.0
                    # y[33]=float(y[33])/16384.0
                    # y[34]=float(y[34])/16384.0
                    # y[35]=float(y[35])/16384.0
                    # y[36]=float(y[36])/131.0
                    # y[37]=float(y[37])/131.0
                    # y[38]=float(y[38])/131.0
                    # y[39]=float(y[39])/16384.0
                    # y[40]=float(y[40])/16384.0
                    # y[41]=float(y[41])/16384.0
                    # y[42]=float(y[42])/131.0
                    # y[43]=float(y[43])/131.0
                    # y[44]=float(y[44])/131.0
                    # y[45]=float(y[45])/16384.0
                    # y[46]=float(y[46])/16384.0
                    # y[47]=float(y[47])/16384.0


                    y1.append(y)
                    print(len(y1))
                if not self.sw and self.dummy % 2==1:
                    self.dummy=0
                    
                    y1=np.array(y1)
                    y1=np.transpose(y1)
                    #headerList=['gyrox1','gyroy1','gyroz1','accelx1','accely1','accelz1','gyrox2','gyroy2','gyroz2','accelx2','accely2','accelz2','gyrox3','gyroy3','gyroz3','accelx3','accely3','accelz3','gyrox4','gyroy4','gyroz4','accelx4','accely4','accelz4',
                    #'gyrox5','gyroy5','gyroz5','accelx5','accely5','accelz5','gyrox6','gyroy6','gyroz6','accelx6','accely6','accelz6','gyrox7','gyroy7','gyroz7','accelx7','accely7','accelz7','gyrox8','gyroy8','gyroz8','accelx8','accely8','accelz8']
                    df = pd.DataFrame(y1).T
                    #df.to_csv(r"C:\Users\Dell\Desktop\MS Bioengineering\imu_data5.csv",header=headerList)
                    df.to_csv(r"C:\Users\Dell\Desktop\MS Bioengineering\imu_data5.csv")
                    y1=[]
               
                # if not self.sw1:
                #     break
                # self.Ax.append(np.array(y[0]))
                # self.Ay.append(np.array(y[1]))
                # self.Az.append(np.array(y[2]))
                # self.Gx.append(np.array(y[3]))
                # self.Gy.append(np.array(y[4]))
                # self.Gz.append(np.array(y[5]))
                # self.Ax1.append(np.array(y[6]))
                # self.Ay1.append(np.array(y[7]))
                # self.Az1.append(np.array(y[8]))
                # self.Gx1.append(np.array(y[9]))
                # self.Gy1.append(np.array(y[10]))
                # self.Gz1.append(np.array(y[11]))
                # if len(self.Ax)>1000:
                #     self.Ax = self.Ax[-1000:]
                #     self.Ay = self.Ay[-1000:]
                #     self.Az = self.Az[-1000:]
                #     self.Gx = self.Gx[-1000:]
                #     self.Gy = self.Gy[-1000:]
                #     self.Gz = self.Gz[-1000:]
                #     self.Ax1 = self.Ax1[-1000:]
                #     self.Ay1 = self.Ay1[-1000:]
                #     self.Az1 = self.Az1[-1000:]
                #     self.Gx1 = self.Gx1[-1000:]
                #     self.Gy1 = self.Gy1[-1000:]
                #     self.Gz1 = self.Gz1[-1000:]
                #     #progress_callback.emit([self.Ax, self.Ay,self.Az,self.Gx,self.Gy,self.Gz, self.Ax1, self.Ay1, self.Az1, self.Gx1, self.Gy1, self.Gz1])
                    
    
            

    def kill_switch1(self, sw1):
        if sw1:
            self.sw1 = True
        if not sw1:
            self.sw1 = False              

    
    def kill_switch(self, sw):
        if sw:
            self.sw = 1
        if not sw:
            self.sw = 0
            
    def connect1(self):
        if self.ser.isOpen():
            self.show=Thread(target=self.show_data,args=())
            self.show.start()  
    # def ConnectToArduino(self,header,filename=' '):
    #     if self.ser.isOpen():
        
    #         #Start reader and writer threads.

    #         reader = Thread(target=self.recordData, args=(header,filename))
            
    #         reader.start()

# B=SerialPort.show_data()   
# print(B)        
#Ui_MainWindow.Pushbutton1.clicked.connect(self.start_record)
#Ui_MainWindow.pushbutton2.clicked.connect(self.stop_record)
# temp=SerialPort('COM6',9600)
# header=['time','gyrox','gyroy','gyroz','accelx','accely','accelz']
# temp.ConnectToArduino(header,r'C:\Users\Dell\Desktop\MS Bioengineering\imu_data5.csv')

# header=['time','gyrox','gyroy','gyroz','accelx','accely','accelz']
# keyboard.wait('enter') 
# with open(r'C:\Users\Dell\Desktop\MS Bioengineering\imu_data3.csv', 'w', encoding='UTF8', newline='') as f:
#     writer = csv.writer(f)
#     writer.writerow(header)
#     current_date_time = datetime.now()
#     while True:
#         try:  
#             if keyboard.is_pressed('esc'):   
#                 print('Recording stopped!')
#                 break  
#         except:
#             break  
#         if temp.serial_read():
#             y=list(struct.unpack('6f',temp.payload))
#             y.insert(0, current_date_time)
#             writer.writerow(y)






