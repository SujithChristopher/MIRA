import serial
from reading_imu_data import SerialPort as pt

serialport=serial.Serial("COM4",115200)
# while 1:
#     print(serialport.read(28))

myport = pt("COM4", 115200)
myport.serial_read()