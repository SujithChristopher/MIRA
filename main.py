import sys
import os
import pickle
import msgpack as mp
import msgpack_numpy as mpn

import shutil
import time
from datetime import date
from datetime import datetime
import ctypes
import cv2
import fpstimer
import numpy as np
from numpy import random
import subprocess
from numba import njit

"""pyside modules"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *

"""this is the mira function class"""
from function_class import Mira_functions  # putting all my main functions here, to organize the code

"""importing pykinect modules"""
from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime

"""importing database functions"""
from support_py.support import db_create
from support_py.support import db_ses_fetch
from support_py.support import db_ses_update
from support_py.support import db_fetch
from support_py.support import db_remove_all
from support_py.support import db_p_select
from support_py.support import save_patient_details

from support_py import timeset
from support_py.color_py import initialize_color
from support_py.color_py import curvy_buttons
from support_py.support import get_clickedtask
from support_py.support import get_calCalibData

from support_py.button_init import initialize_buttons
from support_py.parameter_init import initialize_parameters
from support_py.parameter_init import camera_list_init

from support_py.pymf import get_MF_devices as get_camera_list
from support_py.calibration import calibrate_using_clicked_points

"""importing realsense libraries"""
import pyrealsense2 as rs

"""IMU libraries and functions"""
# import imu_services.imu_2nos as imu
# # from imu_services.imu_2nos import start_imu_service
# import asyncio
# from imu_services.classic_imu_py import reading_imu_data as classic_imu

"""importing settings and creating folders"""

temp_dir = r"C:\mira\temp"

try:
    if os.path.exists(".//src//settings.pickle"):
        sett_file = open(".//src//settings.pickle", "rb")
        sett = pickle.load(sett_file)
        sett_file.close()
        print(f"path: {sett}")
        if not os.path.exists(sett):
            print("Directory not found, setting defaults")
            print("Updating settings file")
            if os.path.exists(r"C:\mira"):
                sett = r"C:\mira"
            else:
                os.makedirs(r"C:\mira")
                sett = r"C:\mira"
            f1 = open(".//src//settings.pickle", "wb")
            pickle.dump(sett, f1)
            f1.close()
        if not os.path.exists(temp_dir):
            os.makedev(temp_dir)

    else:
        print("Settings file not found, setting defaults")
        if os.path.exists(r"C:\mira"):
            sett = r"C:\mira"
        else:
            os.makedirs(r"C:\mira")
            sett = r"C:\mira"
        print("Creating settings file")
        f1 = open(".//src//settings.pickle", "wb")
        pickle.dump(sett, f1)
        f1.close()
except:
    print("Settings file corrupted")
    # sys.exit()


# datetime object containing current date and time
now = datetime.now()
today = date.today()

""""This function packs color, depth, and timeframes and save them in MSGPACK format"""


def save_frames(colorImg, depthImg, milliseconds, colorFile, depthFile, paramsfile, selection, kinect):
    depthframesaveformat = np.copy(np.ctypeslib.as_array(depthImg, shape=(
        kinect._depth_frame_data_capacity.value,)))  # TODO Figure out how to solve intermittent up to 3cm differences

    d_packed = mp.packb(depthframesaveformat, default=mpn.encode)
    depthFile.write(d_packed)

    c_packed = mp.packb(colorImg, default=mpn.encode)
    colorFile.write(c_packed)

    prm = [milliseconds, selection]
    p_packed = mp.packb(prm)
    paramsfile.write(p_packed)


""""initializing pysignals for communicating between threads"""


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(QImage)
    progress = pyqtSignal(QImage)
    changePixmap = pyqtSignal(QImage)


""""threading class"""


class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            pass
        else:
            pass
        finally:
            self.signals.finished.emit()  # Done


"""Main program"""


class MainWindow(Mira_functions):
    xyRectPos = pyqtSignal(int)
    imageStatus = pyqtSignal(str)
    progress_callback = pyqtSignal(QImage)
    newPixmap = pyqtSignal(QImage)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.data_path = sett
        self.data_saved = False
        self.dummy_dir = ""

        self.res_s = False
        self.temp_dir = temp_dir
        self.temp_save = ""

        """get camera list and camera initialization"""
        self.device_list = get_camera_list()

        """initializing different functions"""
        initialize_parameters(self)  # general parameters
        initialize_buttons(self)  # button connections
        db_create(self)  # database initialization
        initialize_color(self)  # color or theme
        curvy_buttons(self)  # button theme
        camera_list_init(self)  # camera list initialization

        self.select_camera = "INTEL"

        self.kinectColor = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color)
        self.kinectDepth = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self.kinect = PyKinectRuntime.PyKinectRuntime(
            PyKinectV2.FrameSourceTypes_Color | PyKinectV2.FrameSourceTypes_Depth)

        # Configure depth and color streams
        self.realsense_pipeline = rs.pipeline()
        self.realsense_config = rs.config()

        # pipeline_wrapper = rs.pipeline_wrapper(self.realsense_pipeline)
        # pipeline_profile = self.realsense_config.resolve(pipeline_wrapper)
        # device = pipeline_profile.get_device()
        # device_product_line = str(device.get_info(rs.camera_info.product_line))

        # if device:

        try:
            self.realsense_config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
            self.realsense_config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)
            self.realsense_pipeline.start(self.realsense_config)  # start the stream
        except:
            pass

        # self.acquireSingleframe()
        self.timerfps = fpstimer.FPSTimer(self.fps_val)

        self.threadpool = QThreadPool()
        print("Multi-threading with maximum %d threads" % self.threadpool.maxThreadCount())

        dt = QDate.currentDate()
        self.dateEdit.setDate(dt)
        self.refreshICN.setIcon(QIcon(r'src\refreshIcon.png'))
        self.keyPressEvent = self.keyboard_events

    """IMU function, for different purposes, this uses external trigger button"""

    def initializeIMU(self):
        """setting time on IMU watch for old sparkfun borads"""
        # a1 = timeset.IMU_Watch().set_time()
        # self.statusBar().showMessage(a1)
        if self.imu_trigger:
            self.imu_trigger = False

            """this IMU is from nano 33 ble/iot"""
            # if self.sessionDir:
            #     self._imu_p = subprocess.Popen(['python', './/imu_services//imu_2nos.py', "-p", self.sessionDir])
            # else:
            #     print("please select patient dir")

            """This is for IMU with classic bluetooth"""

            # myport = classic_imu.SerialPort("COM15", 115200)

            # worker = Worker(myport.run_program)  # Any other args, kwargs are passed to the run function
            # worker.signals.progress.connect(self.do_nothing)
            # worker.signals.finished.connect(self.thread_complete)
            # worker.signals.result.connect(self.thread_complete)
            # self.threadpool.start(worker)
            print("initializing, please wait")

            self._imu_p = subprocess.Popen(
                ['python', './/imu_services//classic_imu_py//reading_imu_data.py', "-p", self.sessionDir])
            # if self.sessionDir:
            #     self._imu_p = subprocess.Popen(['python', './/imu_services//classic_imu_py//reading_imu_data.py'])
            # else:
            #     self._imu_p = subprocess.Popen(['python', './/imu_services//classic_imu_py//reading_imu_data.py'])
            #     print("please select patient dir")
        else:
            print("stopping imu recording")
            self._imu_p.terminate()
            print("imu recording stopped")

    def discardSesFun(self):

        # os.remove(self.colourfilename)
        # os.remove(self.depthfilename)
        try:
            self.data_saved = True
            shutil.rmtree(self.sessionDir)

            # os.remove(self.sessionDir)
            self.newSession.setEnabled(True)
            self.statusBar().showMessage('Recorded session is discarded')
        except:
            pass

    def saveSesFun(self):
        # self.newSession.setEnabled(True)
        self.saveSession.setEnabled(False)
        self.discardSession.setEnabled(False)
        self.newSession.setEnabled(False)
        """
        conversion of depth to camera space in action        
        """
        # msg = camspace(self.sessionDir, self.res_s)
        # Example()
        # print(msg)

        self.statusBar().showMessage('Recorded session is saved successfully')
        db_ses_update(self, self.pDetails[0], self.sessionName, False, False)
        # p = subprocess.Popen(['python', 'pro_bar.py'])
        # self.start_p("wait", 50)
        # Actions().progress_change()
        # shutil.copytree(self.temp_save, self.sessionDir)
        # print("copying completed")
        # shutil.rmtree(self.temp_save)
        # print("temp files removed")

        QMessageBox
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("Recorded session is saved successfully")
        msgBox.setWindowTitle("Saved")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.buttonClicked.connect(self.do_nothing)
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            print('OK clicked')

        self.data_saved = True

    def do_nothing(self):
        pass

    def newSessionFile(self):

        self.newSesBr = True
        self.newSes = True
        self.generalInit()
        self.saveLocation()
        # self.acquireSingleframe()

    def saveLocation_fun(self):

        row = self.p_list_wid.currentRow()
        db_p_select(self, row)

        input_dir = f"{self.data_path}//splitVideos//{self.selected_p}"

        if input_dir is "":
            self.statusBar().showMessage('Please select Patient directory')

        else:
            pFile = open(input_dir + "/PATIENT_DETAILS.pickle", 'rb')
            img2 = pickle.load(pFile)
            h, w, ch = img2.shape
            bytesPerLine = ch * w
            convertToQtFormat = QImage(img2.data.tobytes(), w, h, bytesPerLine, QImage.Format_RGB888)
            p = convertToQtFormat.scaled(100, 100, Qt.KeepAspectRatio)

            self.pProfilePic.setPixmap(QPixmap.fromImage(p))
            self.pDetails = pickle.load(pFile)
            self.savingDir = input_dir
            self.pFileName = self.pDetails[0]
            self.pNameLabel.setText(self.pDetails[1] + " " + self.pDetails[2])
            self.pIDLabel.setText("Patient UID: " + self.pDetails[0])
            self.statusBar().showMessage('Patient directory selected')
            self.dummy_dir = "a"
            self.tabWidget.setCurrentIndex(0)

    def saveLocation(self):
        self.p_open.setEnabled(True)
        self.chooseRoi.setEnabled(True)

        if not self.newSes:
            parent = f"{self.data_path}//splitVideos"
            if os.path.exists(parent):
                pass
            else:
                os.makedirs(parent)

            self.tabWidget.setCurrentIndex(1)

    def savePatientDetails(self):
        save_patient_details(self)

    def startRec(self):
        self.poseFlag = "REC"
        self.hi_res_set.setEnabled(False)
        self.startRecording.setEnabled(False)
        self.stopRecording.setEnabled(True)
        self.show()
        self.statusBar().showMessage('Recording Video...')

    def stopRec(self):
        self.poseFlag = "SREC"
        self.stopRecording.setEnabled(False)
        self.saveSession.setEnabled(True)
        self.saveSession.setStyleSheet("background-color : green")
        self.discardSession.setEnabled(True)
        self.discardSession.setStyleSheet("background-color : red")
        # self.show()
        self.statusBar().showMessage('Stopped recording')

    def updateRect(self, event):
        if self.selected_camera is not None:

            if self.tabWidget.currentIndex() == 0:
                print(event.x(), event.y())
                self.xPos = event.x()
                self.yPos = event.y()
                self.acquireSingleframe()
                self.xyRectPos.emit(self.xPos)

            elif self.tabWidget.currentIndex() == 1:
                self.xPos = event.x()
                self.yPos = event.y()
                self.acquireSingleframe(1)
                self.xyRectPos.emit(self.xPos)

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.displayLabel.setPixmap(QPixmap.fromImage(image))

    def initUI(self):

        self.task_group.show()
        self.poseFlag = "POSE"
        self.imageStatus.emit(self.poseFlag)
        self.chooseRoi.setEnabled(False)
        self.startRecording.setEnabled(True)
        self.xy = [self.xPos * 2, self.yPos * 2]
        self.statusBar().showMessage('ROI selected')

        if not self.newSes:
            worker = Worker(self.readFrame)  # Any other args, kwargs are passed to the run function
            worker.signals.progress.connect(self.setImage)
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.result.connect(self.thread_complete)
            self.threadpool.start(worker)

        self.show()

    def thread_complete(self):
        print("THREAD COMPLETE!")

    def acquireSingleframe(self, tab_no=0):

        if self.select_camera == "KINECT":
            if self.kinectColor.has_new_color_frame() and self.kinectDepth.has_new_depth_frame():
                colorFrame = self.kinectColor.get_last_color_frame()
                colorFrame = colorFrame.reshape((1080, 1920, 4))
                img = cv2.cvtColor(colorFrame, cv2.COLOR_BGRA2RGB)

        if self.select_camera == "CAMERA":
            pass

        if self.select_camera == "INTEL":
            frames = self.realsense_pipeline.wait_for_frames()
            colorFrame = frames.get_color_frame()
            colorFrame = np.asanyarray(colorFrame.get_data())
            img = cv2.cvtColor(colorFrame, cv2.COLOR_BGR2RGB)

        try:
            if self.poseFlag == "RECT":

                if self.capF:
                    """
                    This is for capturing profile picture
                    """
                    img2 = img[200:200 + 736, 600:600 + 864].copy()
                    h, w, ch = img2.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QImage(img2.data.tobytes(), w, h, bytesPerLine, QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
                    self.profilePicture = img2
                    self.profilePictureLabel1.setPixmap(QPixmap.fromImage(p))

                elif self.calib:
                    p = calibrate_using_clicked_points(self, img)

                    self.xyRectPos.emit(self.xPos)
                    painter.end()
                    self.displayLabel.setPixmap(QPixmap.fromImage(p))

                else:
                    """
                    This is for displaying rectangle
                    """
                    h, w, ch = img.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QImage(img.data.tobytes(), w, h, bytesPerLine, QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
                    painter = QPainter(p)
                    painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                    painter.drawRect(self.xPos, self.yPos, 432, 368)
                    painter.end()
                    self.xyRectPos.emit(self.xPos)
                    if tab_no == 1:
                        self.frame_display.setPixmap(QPixmap.fromImage(p))
                    else:
                        self.displayLabel.setPixmap(QPixmap.fromImage(p))
        except:
            pass

    def createFile(self, fileCounter):
        self.d1 = today.strftime("%d-%m-%y")
        self.tm1 = self.dateEdit.date().toString("dd-MM-yy")
        self.tm2 = now.strftime("%H-%M-%S")
        self.tM = self.tm1 + " " + self.tm2
        self.tm = self.tm1 + "_" + self.tm2

        if fileCounter == 1:
            self.rnd = random.randint(999)
            self.sessionName = "Session " + self.tm1 + "_" + self.tm2 + "_" + str(self.rnd)
            self.sessionDir = os.path.join(self.savingDir, self.sessionName)
            self.temp_save = os.path.join(self.temp_dir, self.sessionName)
            os.mkdir(self.sessionDir)

            self.parmsFileName = self.sessionDir + "/" + "PARAMS" + "_" + self.tm + "_" + str(
                self.rnd) + ".msgpack"

            self.paramFile = open(self.parmsFileName, 'wb')

            # Define writer with defined parameters and suitable output filename for e.g. `Output.mp4`
            self.vid_filename = self.sessionDir + "/" + "Video.avi"

            if self.res_s:
                self.cv_writer = cv2.VideoWriter(self.vid_filename, cv2.VideoWriter_fourcc(*'XVID'), self.fps_val,
                                                 ((864, 736)))
            else:
                self.cv_writer = cv2.VideoWriter(self.vid_filename, cv2.VideoWriter_fourcc(*'XVID'), self.fps_val,
                                                 ((432, 368)))

            try:
                if self.calibPlot:
                    file = open(self.sessionDir + "/" + "CALIBDATA" + "_" + self.tm + "_" +
                                str(self.rnd) + ".pickle", "wb")
                    pickle.dump(self.calibOrg, file)
                    pickle.dump(self.calibRotM, file)
                    file.close()
                    self.calibPlot = False
            except:
                pass

        self.commonName = self.pFileName + " " + self.tM + " " + str(self.rnd)
        self.depthfilename = self.sessionDir + "/" + "DEPTH" + "_" + self.tm + "_" + str(
            self.rnd) + "_" + str(fileCounter) + ".msgpack"
        self.colourfilename = self.sessionDir + "/" + "COLOUR" + "_" + self.tm + "_" + str(
            self.rnd) + "_" + str(fileCounter) + ".msgpack"
        self.depthfile = open(self.depthfilename, 'wb')
        self.colourfile = open(self.colourfilename, 'wb')

        print(f"creating files {fileCounter}")

    """main function for read, disp, save camera frames"""

    def readFrame(self, progress_callback):

        if self.fx_roi:
            yPos = 112
            xPos = 274
            yRes = self.yRes
            xRes = self.xRes

        else:
            yPos = self.yPos
            xPos = self.xPos
            yRes = self.yRes
            xRes = self.xRes

        self.counter = 1
        self.fileCounter = 1

        self.createFile(self.fileCounter)
        p_packed = mp.packb(self.xy)
        self.paramFile.write(p_packed)
        p_packed = mp.packb(2)
        self.paramFile.write(p_packed)

        new_frame_time = 0
        prev_frame_time = 0

        @njit
        def numba_resize(colorFrame, depthFrame, yPos, xPos, yRes, xRes, scalling, camera=0):
            if camera == 1:
                colorFrame = colorFrame.reshape((1080, 1920, 4))  # 1920 c x 1080 r with 4 bytes (BGRA) per pixel
            colorFrame = colorFrame[yPos * scalling:yPos * scalling + yRes,
                         xPos * scalling:xPos * scalling + xRes].copy()
            if camera == 1:
                depthFrame = np.reshape(depthFrame, (424, 512))
            return colorFrame, depthFrame

        while True:

            if self.select_camera == "KINECT":
                if self.kinectColor.has_new_color_frame() and self.kinectDepth.has_new_depth_frame():
                    colorFrame = self.kinectColor.get_last_color_frame()
                    depthFrame = self.kinectDepth.get_last_depth_frame()

            elif self.select_camera == "CAMERA":
                pass

            elif self.select_camera == "INTEL":
                frames = self.realsense_pipeline.wait_for_frames()
                colorFrame = frames.get_color_frame()
                colorFrame = np.asanyarray(colorFrame.get_data())
                depthFrame = frames.get_depth_frame()
                depthFrame = np.asanyarray(depthFrame.get_data())

            timestamp = str(datetime.now())

            colorFrame, depthFrame = numba_resize(colorFrame, depthFrame, yPos, xPos, yRes, xRes, 2)
            if self.select_camera == "KINECT":
                colorFrame = cv2.cvtColor(colorFrame, cv2.COLOR_BGRA2RGB)
            elif self.select_camera == "INTEL":
                colorFrame = cv2.cvtColor(colorFrame, cv2.COLOR_BGR2RGB)

            new_frame_time = time.time()
            if self.res_s:
                imageSave = colorFrame
            else:
                imageSave = cv2.resize(colorFrame, (432, 368))

            if self.select_camera == "INTEL":
                depthFrame = cv2.resize(depthFrame, (424, 512))

            imgSaveBGR = cv2.cvtColor(imageSave, cv2.COLOR_RGB2BGR)

            self.colorImage = colorFrame
            self.depthImage = depthFrame

            flpimg = cv2.flip(self.colorImage, 1)
            h1, w1, ch = flpimg.shape
            bytesPerLine = ch * w1
            convertToQtFormat = QImage(flpimg.data.tobytes(), w1, h1, bytesPerLine, QImage.Format_RGB888)

            p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
            progress_callback.emit(p)

            if self.counter == 90:
                self.fileCounter = self.fileCounter + 1
                self.colourfile.close()
                self.depthfile.close()
                self.createFile(self.fileCounter)
                self.counter = 1

            if self.poseFlag == "REC":
                kinect = self.kinect
                selection = get_clickedtask(self)
                save_frames(imgSaveBGR, depthFrame, timestamp, self.colourfile, self.depthfile, self.paramFile,
                            selection, kinect)
                self.cv_writer.write(imgSaveBGR)
                self.counter = self.counter + 1
                fps = 1 / (new_frame_time - prev_frame_time)
                prev_frame_time = new_frame_time
                # print(str(fps))

            elif self.poseFlag == "SREC":
                self.colourfile.close()
                self.depthfile.close()
                self.paramFile.close()
                self.cv_writer.release()
                self.poseFlag = "ABC"

            self.timerfps.sleep()

            if self.newSesBr:
                break


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    # ImageUpdate()
    w.show()
    sys.exit(app.exec_())
