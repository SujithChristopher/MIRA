import serial
import serial.tools.list_ports
from datetime import datetime
import calendar

SETTIME = 6


class IMU_Watch(object):

    def __init__(self, serialrate=115200):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()

        # Looks for a watch until it finds one
        running = False
        while True:
            ports = list(serial.tools.list_ports.comports())
            ports = [str(p.device) for p in ports if str(p.hwid).find('9D0F') > 0]
            if len(ports) == 0:
                print('Watch not found')
            else:
                break
        self.serialport = ports[0]
        # Initialise serial port
        self.ser = serial.Serial(self.serialport, serialrate)
        while not running:
            if self.ser.isOpen():
                print('Watch found at ', self.serialport)
                running = True
            else:
                print('Cannot open %s. Trying again...', self.serialport)
                self.ser.open()

    def serial_write(self, command, string=''):
        # Format:
        # | 255 | 255 | no. of bytes | command | filename/time | checksum |

        header = [255, 255]
        chksum = 254

        payload_size = len(string) + 1

        chksum += payload_size + command

        self.ser.write(bytes([header[0]]))
        self.ser.write(bytes([header[1]]))
        self.ser.write(bytes([payload_size]))

        self.ser.write(bytes([command]))

        if string != '':
            for i in range(len(string)):
                self.ser.write(bytes([ord(string[i])]))
                chksum += ord(string[i])

        self.ser.write(bytes([chksum % 256]))

    def serial_read(self):
        if (self.ser.read() == b'\xff') and (self.ser.read() == b'\xff'):
            self.count += 1
            chksum = 255 + 255

            sz = self.ser.read(2)
            self.plSz = int.from_bytes(sz, 'little')
            chksum += sum(sz)

            self.payload = self.ser.read(self.plSz)
            chksum += sum(self.payload)
            chksum = bytes([chksum % 256])
            _chksum = self.ser.read()

            return _chksum == chksum
        return False

    def set_time(self):
        # Sends current time from PC and reads the time set on the IMU watch
        unix = calendar.timegm(datetime.now().timetuple())
        self.serial_write(SETTIME, string=str(unix))
        # self.statusBar().showMessage("Initialized IMU watch")
        print('Command sent: SETTIME - ', datetime.utcfromtimestamp(unix).strftime('%Y-%m-%d %H:%M:%S'))
        if self.serial_read():
            unix = int(self.payload.decode('utf-8'))
            a = ('Time on Watch: ' + datetime.utcfromtimestamp(unix).strftime('%Y-%m-%d %H:%M:%S'))
        return a