import sys
import os
import pickle
from matplotlib.pyplot import sca
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
import pandas as pd
import subprocess
from numba import njit

"""pyside modules"""

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *

"""this is the main design file"""
from guiDesign import Ui_MainWindow

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

from support_py.pymf import get_MF_devices

"""importing realsense libraries"""
import pyrealsense2 as rs

"""IMU libraries and functions"""
import imu_services.imu_2nos as imu
# from imu_services.imu_2nos import start_imu_service
import asyncio
from imu_services.classic_imu_py import reading_imu_data as classic_imu

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

try:
    fRenamePth = r"C:\Users\CMC\Documents\openposelibs\pose\data"
    os.rename(fRenamePth + "/toAnalyse.txt", fRenamePth + "/toAnalyse_.txt")
except:
    pass

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


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
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
        self.device_list = get_MF_devices()
       

        """initializing different functions"""
        initialize_parameters(self)  # general parameters
        initialize_buttons(self)  # button connections
        db_create(self)  # database initialization
        initialize_color(self)  # color or theme
        curvy_buttons(self)  # button theme
        camera_list_init(self)  # camera list initialization

        self.select_camera = "KINECT"


        self.kinectColor = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color)
        self.kinectDepth = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)
        self.kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color | PyKinectV2.FrameSourceTypes_Depth)

        # self.acquireSingleframe()
        self.timerfps = fpstimer.FPSTimer(self.fps_val)

        self.threadpool = QThreadPool()
        print("Multi-threading with maximum %d threads" % self.threadpool.maxThreadCount())

        dt = QDate.currentDate()
        self.dateEdit.setDate(dt)
        self.refreshICN.setIcon(QIcon(r'src\refreshIcon.png'))
        self.keyPressEvent = self.keyboard_events

        

    def keyboard_events(self, event):
        if event.key() == Qt.Key_Escape:
            self.uns.setChecked(True)

    def closeEvent(self, event):
        if (not self.data_saved) and (self.dummy_dir is not ""):
            close = QtWidgets.QMessageBox.question(self,
                                                   "QUIT",
                                                   "Do you want to save the current session",
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            if close == QtWidgets.QMessageBox.Yes:
                self.saveSesFun()
                event.accept()
            if close == QtWidgets.QMessageBox.No:
                self.discardSesFun()
                event.accept()
            print("closing")
            self.conn.close()
            self.sconn.close()

    def camera_list_clicked(self):
        
        inx = self.camera_list.currentRow()
        _selected = self.device_list[inx]

        if _selected.startswith("Kinect"):
            self.selected_camera = "KINECT"

        elif _selected.startswith("Intel"):
            self.selected_camera = "INTEL"

        else:
            self.selected_camera = "WEBCAM"

        print(self.selected_camera)

    def fix_roifun(self):
        if self.fix_roi.isChecked():
            self.fx_roi = True
        else:
            self.fx_roi = False

    def res_sett(self):
        if self.hi_res_set.isChecked():
            self.res_s = True
        else:
            self.res_s = False

    def list_clicked(self):

        row = self.p_list_wid.currentRow()
        db_p_select(self, row)

    def ses_clicked(self):
        row = self.p_ses_wid.currentRow()
        ses_name = self.ses_list[row]
        p_uid = self.selected_p
        n_pth = f"{self.data_path}//splitVideos//{p_uid}//{ses_name}//Video.avi"
        self.openFile(n_pth)

    def path_browse_fun(self):

        self.temp_path = QFileDialog.getExistingDirectory(None, 'Select a data folder:', QDir.homePath())
        self.statusBar().showMessage("Data path selected")

    def sett_save_fun(self):

        if self.temp_path == "":
            self.statusbar.showMessage("Choose a directory")
        else:
            pth = f".//src//settings.pickle"
            if os.path.exists(pth):
                sett_file = open(pth, "wb")
                pickle.dump(self.temp_path, sett_file)
                sett_file.close()
                try:
                    if os.path.exists(".//src//settings.pickle"):
                        sett_file = open(".//src//settings.pickle", "rb")
                        sett = pickle.load(sett_file)
                        sett_file.close()
                        print(f"path: {sett}")
                    else:
                        print("Settings file not found, ending program")
                        sys.exit()
                except:
                    print("Settings file corrupted")
                    sys.exit()
            else:
                self.statusBar().showMessage("Something went wrong")
            QMessageBox
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Restart application to refresh data path")
            msgBox.setWindowTitle("Restart")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.buttonClicked.connect(self.exit_program)

            returnValue = msgBox.exec()
            if returnValue == QMessageBox.Ok:
                print('OK clicked')

    def exit_program(self):
        sys.exit()

    """ video playing functions """

    def openFile(self, fileName):
        # fileName, _ = QFileDialog.getOpenFileName(self, "Open Movie",
        #                                           QDir.homePath())
        print(fileName)
        if fileName != '':
            self.mediaPlayer.setMedia(
                QMediaContent(QUrl.fromLocalFile(fileName)))
            self.vid_play.setEnabled(True)
            # print("success")

        db_fetch(self)
        # print("success2")

    def exitCall(self):
        sys.exit(app.exec_())

    def play(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            # pass
        else:
            self.mediaPlayer.play()

    def mediaStateChanged(self, state):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.vid_play.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.vid_play.setIcon(
                self.style().standardIcon(QStyle.SP_MediaPlay))

    def positionChanged(self, position):
        self.vid_slider.setValue(position)

    def durationChanged(self, duration):
        self.vid_slider.setRange(0, duration)

    def setPosition(self, position):
        self.mediaPlayer.setPosition(position)

    def handleError(self):
        self.vid_play.setEnabled(False)
        # print("error")
        # self.vid_player.setText("Error: " + self.mediaPlayer.errorString())
        self.statusBar().showMessage("Error: " + self.mediaPlayer.errorString())

    
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

    def select_task(self, event):
        print(get_clickedtask(self))

    def resetXYZFun(self):
        self.calibCounter = 0
        self.calibXYZ = []
        self.selectXYZ.setText("Select 'O'")
        self.acquireSingleframe()

    def select_fun(self):

        self.calibCounter = self.calibCounter + 1
        self.calibXYZ.append((self.xPos, self.yPos))  # Store 1st position
        self.calibXYZrs.append((self.xPos * 2, self.yPos * 2))
        if self.calibCounter == 1:
            self.selectXYZ.setText("Select X")
        elif self.calibCounter == 2:
            self.selectXYZ.setText("Select Y")
        elif self.calibCounter == 3:
            self.selectXYZ.setText("Show Calib")
            self.calibDepth = self.kinectDepth.get_last_depth_frame()
            self.calibPlot = True
            self.calCalibData()
        elif self.calibCounter == 4:
            self.selectXYZ.setText("Save Calib")
            self.saveCalib()

    def saveCalib(self):
        if self.calibPlot:
            self.calib = False
            print("Calibration will be saved during recording")
        else:
            print("No Calibration values found")

    def calCalibData(self):
        get_calCalibData(self)

    def calibrateFun(self):
        self.calibrate.hide()
        self.exFun.hide()
        self.calib = True
        self.acquireSingleframe()

    def capProfile(self):
        self.capF = True
        self.acquireSingleframe()
        self.capF = False

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
        print(event.x(), event.y())
        self.xPos = event.x()
        self.yPos = event.y()
        self.acquireSingleframe()
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

    def acquireSingleframe(self):

        if self.poseFlag == "RECT":
            if self.kinectColor.has_new_color_frame() and self.kinectDepth.has_new_depth_frame():
                colorFrame1 = self.kinectColor.get_last_color_frame()
                colorFrame = colorFrame1.reshape((1080, 1920, 4))

                img = cv2.cvtColor(colorFrame, cv2.COLOR_BGRA2RGB)

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
                    """
                    the following is picking calibration points
                    """
                    h, w, ch = img.shape
                    bytesPerLine = ch * w
                    convertToQtFormat = QImage(img.data.tobytes(), w, h, bytesPerLine, QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
                    painter = QPainter(p)

                    if self.calibCounter == 0:
                        painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                        painter.drawEllipse(self.xPos, self.yPos, 5, 5)

                    elif self.calibCounter == 1:
                        painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                        painter.drawEllipse(self.calibXYZ[0][0], self.calibXYZ[0][1], 5, 5)
                        painter.setPen(QPen(Qt.blue, 3, Qt.SolidLine))
                        painter.drawEllipse(self.xPos, self.yPos, 5, 5)

                    elif self.calibCounter == 2:
                        painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                        painter.drawEllipse(self.calibXYZ[0][0], self.calibXYZ[0][1], 5, 5)
                        painter.setPen(QPen(Qt.blue, 3, Qt.SolidLine))
                        painter.drawEllipse(self.calibXYZ[1][0], self.calibXYZ[1][1], 5, 5)
                        painter.setPen(QPen(Qt.green, 3, Qt.SolidLine))
                        painter.drawEllipse(self.xPos, self.yPos, 5, 5)

                    elif self.calibCounter > 2:
                        painter.setPen(QPen(Qt.red, 3, Qt.SolidLine))
                        painter.drawLine(self.calibXYZ[0][0] + 2, self.calibXYZ[0][1] + 2, self.calibXYZ[1][0] + 2,
                                         self.calibXYZ[1][1] + 2)
                        painter.drawEllipse(self.calibXYZ[0][0], self.calibXYZ[0][1], 5, 5)
                        painter.setPen(QPen(Qt.blue, 3, Qt.SolidLine))
                        painter.drawLine(self.calibXYZ[2][0] + 2, self.calibXYZ[2][1] + 2, self.calibXYZ[0][0] + 2,
                                         self.calibXYZ[0][1] + 2)
                        painter.drawEllipse(self.calibXYZ[1][0], self.calibXYZ[1][1], 5, 5)
                        painter.setPen(QPen(Qt.green, 3, Qt.SolidLine))
                        painter.drawLine(self.calibXYZ[0][0] + 2, self.calibXYZ[0][1] + 2, self.calibXYZ[0][0] + 2,
                                         self.calibXYZ[0][1] - 50)
                        painter.drawEllipse(self.calibXYZ[2][0], self.calibXYZ[2][1], 5, 5)

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
                    self.displayLabel.setPixmap(QPixmap.fromImage(p))

    def createFile(self, fileCounter):
        self.d1 = today.strftime("%d-%m-%y")
        # self.tm1 = now.strftime("%d-%m-%y")
        self.tm1 = self.dateEdit.date().toString("dd-MM-yy")
        self.tm2 = now.strftime("%H-%M-%S")
        self.tM = self.tm1 + " " + self.tm2
        self.tm = self.tm1 + "_" + self.tm2

        if fileCounter == 1:
            self.rnd = random.randint(999)
            self.sessionName = "Session " + self.tm1 + "_" + self.tm2 + "_" + str(self.rnd)
            self.sessionDir = os.path.join(self.savingDir, self.sessionName)
            self.temp_save = os.path.join(self.temp_dir, self.sessionName)
            # os.mkdir(self.sessionDir)
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
        def numba_resize(colorFrame, depthFrame, yPos, xPos, yRes, xRes, scalling):

            colorFrame = colorFrame.reshape((1080, 1920, 4))  # 1920 c x 1080 r with 4 bytes (BGRA) per pixel
            colorFrame = colorFrame[yPos * scalling:yPos * scalling + yRes, xPos * scalling:xPos * scalling + xRes].copy()
            depthFrame = np.reshape(depthFrame, (424, 512))
            return colorFrame, depthFrame

        while True:            
            if self.kinectColor.has_new_color_frame() and self.kinectDepth.has_new_depth_frame():
                colorFrame = self.kinectColor.get_last_color_frame()  # PyKinect2 returns a color frame in a linear array of size (8294400,)
                depthFrame = self.kinectDepth.get_last_depth_frame()

                timestamp = str(datetime.now())     
                
                colorFrame, depthFrame = numba_resize(colorFrame, depthFrame, yPos, xPos, yRes, xRes, 2)

                # colorFrame = colorFrame.reshape((1080, 1920, 4))  # 1920 c x 1080 r with 4 bytes (BGRA) per pixel

                colorFrame = cv2.cvtColor(colorFrame, cv2.COLOR_BGRA2RGB)
                # image = img[yPos * 2:yPos * 2 + yRes, xPos * 2:xPos * 2 + xRes].copy()

                new_frame_time = time.time()
                if self.res_s:
                    imageSave = colorFrame
                else:
                    imageSave = cv2.resize(colorFrame, (432, 368))

                imgSaveBGR = cv2.cvtColor(imageSave, cv2.COLOR_RGB2BGR)
                # depthFrame = np.reshape(depthFrame, (424, 512))

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
                    # self.createFile(self.fileCounter)
                    self.createFile(self.fileCounter)
                    self.counter = 1

                if self.poseFlag == "REC":
                    kinect = self.kinect
                    selection = get_clickedtask(self)
                    save_frames(imgSaveBGR, depthFrame, timestamp, self.colourfile, self.depthfile, self.paramFile,
                                selection, kinect)
                    self.cv_writer.write(imgSaveBGR)

                    # self.vid_writer.write(imageSave, rgb_mode=True)
                    self.counter = self.counter + 1
                    # print(self.counter)
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
