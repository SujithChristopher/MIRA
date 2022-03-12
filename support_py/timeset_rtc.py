from numpy import byte
import serial
import serial.tools.list_ports
from datetime import datetime
# import calendar
from operator import attrgetter

SETTIME = 6
attrs = ('year', 'month', 'day', 'hour', 'minute', 'second', 'microsecond')


class IMU_Watch(object):

    def __init__(self, serialrate=115200):
        # Initialise serial payload
        self.count = 0
        self.plSz = 0
        self.payload = bytearray()

        # Looks for a watch until it finds one
        running = False
        # while True:
        # ports = list(serial.tools.list_ports.comports())
        # ports = [str(p.device) for p in ports if str(p.hwid).find('9D0F') > 0]
        # if len(ports) == 0:
        #     print('Watch not found')
        # else:
        #     break
        self.serialport = "COM17"
        # Initialise serial port
        self.ser = serial.Serial(self.serialport, serialrate)
        while not running:
            if self.ser.isOpen():
                print('Watch found at ', self.serialport)
                running = True
            else:
                print('Cannot open %s. Trying again...', self.serialport)
                self.ser.open()

    def serial_write(self, _time):
        # Format:
        # | 255 | 255 | no. of bytes | command | filename/time | checksum |
        print("writing")
        header = [255, 255]
        chksum = 0

        payload_size = len(_time) + 1
        print("length of time", len(_time))

        # chksum += payload_size

        self.ser.write(bytes([header[0]]))
        self.ser.write(bytes([header[1]]))
        self.ser.write(bytes([payload_size]))
        # self.ser.write(bytes([command]))

        if _time:
            for count, value in enumerate(list(_time)):
                self.ser.write(byte([ord(value)]))
                # print("count num", count)
                chksum += 1
                print("this is chksum", chksum)
        chksum += 1
        print("this is chksum", [chksum])
        self.ser.write(bytes([chksum % 256]))
        print("done")
        # if self.ser.isOpen():
        #     self.ser.close()

    def serial_read(self):
        if (self.ser.read() == b'\xff') and (self.ser.read() == b'\xff'):
            self.count += 1
            chksum = 255 + 255

            sz = self.ser.read(2)
            self.plSz = int.from_bytes(sz, 'little')
            chksum += sum(sz)

            self.payload = self.ser.read(self.plSz)
            chksum += sum(self.payload)

            print("this is chksum", [chksum % 256])
            chksum = bytes([chksum % 256])
            _chksum = self.ser.read()

            return _chksum == chksum
        return False

    def set_time(self):
        # Sends current time from PC and reads the time set on the IMU watch
        d = datetime.now()
        d_tuple = attrgetter(*attrs)(d)
        t_list = list(d_tuple)
        t_string = ''.join([str(elem) for elem in t_list])

        self.serial_write(t_string)
        # self.statusBar().showMessage("Initialized IMU watch")
        print('Command sent: SETTIME - ', t_string)
        c = 0
        stp = None
        while True:
            # if self.ser.available():
            if self.serial_read():
                print(self.payload)

                print("available")

            # if c < 2:
            #     a = int.from_bytes(self.ser.read(), byteorder='little')
            #     print(a, c)
            #
            # elif c == 2:
            #     a = int.from_bytes(self.ser.read(), byteorder='little')
            #     print(a, c)
            #     stp = a
            #     # print("this is stp", stp)
            #
            # elif c == stp + 2:
            #     a = int.from_bytes(self.ser.read(), byteorder='little')
            #     print(a, c)
            #
            # else:
            #     b = chr(int.from_bytes(self.ser.read(), byteorder='little'))
            #     print(b, c)
            # c += 1


            # unix = int(self.payload.decode('utf-8'))

        # if self.serial_read():
        #     # d_tuple = int(self.payload.decode('utf-8'))
        #     print("reading")
        #     print(self.payload)
        # else:
        #     print("else")
        #     print(self.ser.read())
        #     a = ('Time on Watch: ' + str(self.payload))
        # return a


if __name__ == '__main__':
    a1 = IMU_Watch()
    a1.set_time()
