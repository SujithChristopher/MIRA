import sys
# sys.path.insert(0, ".//include")
# sys.path.insert(1, ".//support_py")
import os
import pickle
import msgpack as mp
import msgpack_numpy as mpn

import shutil
import subprocess
import time
from datetime import date
from datetime import datetime
import ctypes
import cv2
import fpstimer
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *
from numpy import random

from support_py.support import db_create
from support_py.support import db_ses_fetch
from support_py.support import db_ses_update

from pykinect2 import PyKinectV2
from pykinect2 import PyKinectRuntime

from support_py import timeset
from support_py.color_py import initialize_color
from guiDesignV3 import Ui_MainWindow
from support_py.support import get_clickedtask
from support_py.support import get_calCalibData

from support_py.support import save_patient_details
from support_py.support import db_fetch
from support_py.support import db_remove_all
from support_py.support import db_p_select

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

kinectColor = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color)
kinectDepth = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Depth)

kinect = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Color | PyKinectV2.FrameSourceTypes_Depth)


def saveFrames(colorImg, depthImg, milliseconds, colorFile, depthFile, paramsfile, selection):
    depthframesaveformat = np.copy(np.ctypeslib.as_array(depthImg, shape=(
        kinect._depth_frame_data_capacity.value,)))  # TODO Figure out how to solve intermittent up to 3cm differences

    d_packed = mp.packb(depthframesaveformat, default=mpn.encode)
    depthFile.write(d_packed)

    c_packed = mp.packb(colorImg, default=mpn.encode)
    colorFile.write(c_packed)

    prm = [milliseconds, selection]
    p_packed = mp.packb(prm)
    paramsfile.write(p_packed)


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(QImage)
    progress = pyqtSignal(QImage)
    changePixmap = pyqtSignal(QImage)


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


def append_new_line(file_name, text_to_append):
    """Append given text as a new line at the end of file"""
    # Open the file in append & read mode ('a+')
    with open(file_name, "a+") as file_object:
        # Move read cursor to the start of file.
        file_object.seek(0)
        # If file is not empty then append '\n'
        data = file_object.read(100)
        if len(data) > 0:
            file_object.write("\n")
        # Append text at the end of file
        file_object.write(text_to_append)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    xyRectPos = pyqtSignal(int)
    imageStatus = pyqtSignal(str)
    progress_callback = pyqtSignal(QImage)
    newPixmap = pyqtSignal(QImage)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.yRes = 736
        self.xRes = 864

        self.xPos = 0
        self.yPos = 0

        self.fps_val = 15

        self.setupUi(self)
        self.poseFlag = "RECT"
        self.dataFlag = 0

        self.newSes = False
        self.capF = False
        self.newSesBr = False
        self.calib = False

        # self.initUI()
        self.generalInit()
        self.acquireSingleframe()
        self.profilePicture = None

        self.timerfps = fpstimer.FPSTimer(self.fps_val)

        # self.chooseRoi.clicked.connect(self.acquireSingleframe)
        self.displayLabel.mousePressEvent = self.updateRect
        self.task_group.hide()
        self.task_group.mousePressEvent = self.select_task
        self.calibXYZ = []
        self.calibXYZrs = []

        self.threadpool = QThreadPool()
        print("Multi-threading with maximum %d threads" % self.threadpool.maxThreadCount())

        dt = QDate.currentDate()
        self.dateEdit.setDate(dt)
        self.refreshICN.setIcon(QIcon(r'src\refreshIcon.png'))

        self.globDate = self.dateEdit.date()

        self.statusBar().showMessage("Initialized")
        # self.statusBar().setStyleSheet("border :3px solid black;")
        self.statusBar().setFont(QFont('Times', 12))
        self.calibCounter = 0
        self.keyPressEvent = self.keyboard_events
        self.data_path = sett
        self.data_saved = False
        self.dummy_dir = ""

        db_create(self)
        initialize_color(self)
        self.res_s = False
        self.temp_dir = temp_dir
        self.temp_save = ""

        """
        Fixed roi parameters
        """
        self.fx_roi = False

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

    def generalInit(self):

        """
        First Tab: Initializing buttons
        """

        self.chooseRoi.clicked.connect(self.initUI)
        self.startRecording.setEnabled(False)
        self.startRecording.clicked.connect(self.startRec)
        self.stopRecording.setEnabled(False)
        self.stopRecording.clicked.connect(self.stopRec)
        self.saveDetails.clicked.connect(self.savePatientDetails)
        self.browseLocation.clicked.connect(self.saveLocation)
        self.newSession.setEnabled(False)
        self.newSession.clicked.connect(self.newSessionFile)
        self.discardSession.setEnabled(False)
        self.discardSession.clicked.connect(self.discardSesFun)
        self.saveSession.setEnabled(False)
        self.saveSession.clicked.connect(self.saveSesFun)

        self.calibrate.clicked.connect(self.calibrateFun)
        self.selectXYZ.clicked.connect(self.selectFun)
        self.resetXYZ.clicked.connect(self.resetXYZFun)
        self.hi_res_set.clicked.connect(self.res_sett)
        # roi settings
        self.fix_roi.clicked.connect(self.fix_roifun)

        if self.newSes:
            self.chooseRoi.setEnabled(True)
        else:
            self.chooseRoi.setEnabled(False)

        # self.uns.clicked.connect(self.select_task)
        self.exFun.clicked.connect(self.initializeIMU)

        """
        Second Tab: Patient details
        """
        self.saveDetailsCapture.clicked.connect(self.capProfile)

        """
        settings tab
        """
        self.path_browse.clicked.connect(self.path_browse_fun)
        self.sett_save.clicked.connect(self.sett_save_fun)

        """
        Patient directory: playing video tab
        """
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        videoWidget = self.vid_widget

        self.vid_play.clicked.connect(self.play)

        self.vid_slider.setRange(0, 0)
        self.vid_slider.sliderMoved.connect(self.setPosition)

        self.errorLabel = self.statusBar

        # self.vid_pause.clicked.connect(self.openFile)

        self.mediaPlayer.setVideoOutput(videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)
        # list widget
        self.p_list_wid.itemClicked.connect(self.list_clicked)
        self.p_ses_wid.itemClicked.connect(self.ses_clicked)
        self.p_open.setEnabled(False)
        self.p_open.clicked.connect(self.saveLocation_fun)

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

        fname = QFileDialog.getExistingDirectory(None, 'Select a data folder:', QDir.homePath())
        self.temp_path = fname
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

    def initializeIMU(self):
        a1 = timeset.IMU_Watch().set_time()
        self.statusBar().showMessage(a1)
        pass

    def select_task(self, event):
        print(get_clickedtask(self))

    def resetXYZFun(self):
        self.calibCounter = 0
        self.calibXYZ = []
        self.selectXYZ.setText("Select 'O'")
        self.acquireSingleframe()

    def selectFun(self):

        self.calibCounter = self.calibCounter + 1
        self.calibXYZ.append((self.xPos, self.yPos))  # Store 1st position
        self.calibXYZrs.append((self.xPos * 2, self.yPos * 2))
        if self.calibCounter == 1:
            self.selectXYZ.setText("Select X")
        elif self.calibCounter == 2:
            self.selectXYZ.setText("Select Y")
        elif self.calibCounter == 3:
            self.selectXYZ.setText("Show Calib")
            self.calibDepth = kinectDepth.get_last_depth_frame()
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

        # input_dir = QFileDialog.getExistingDirectory(None, 'Select a folder:', parent)
        # print(input_dir)
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

        """
        Opening pickle files for verification
        """
        # fp = open(self.parmsFileName, "rb")
        # f1 = pickle.load(fp)
        # f2 = pickle.load(fp)
        # print(f1)
        # print(f2)

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
            if kinectColor.has_new_color_frame() and kinectDepth.has_new_depth_frame():
                colorFrame1 = kinectColor.get_last_color_frame()
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
        # paramsfile.write(p_packed)
        #
        # pickle.dump(self.xy, self.paramFile)
        # pickle.dump(2, self.paramFile)

        starttime = time.time()
        new_frame_time = 0
        prev_frame_time = 0

        while True:
            if kinectColor.has_new_color_frame() and kinectDepth.has_new_depth_frame():
                start1 = time.time()
                colorFrame1 = kinectColor.get_last_color_frame()  # PyKinect2 returns a color frame in a linear array of size (8294400,)
                depthFrame = kinectDepth.get_last_depth_frame()

                # timestamp = time.time() - starttime
                timestamp = str(datetime.now())

                colorFrame = colorFrame1.reshape((1080, 1920, 4))  # 1920 c x 1080 r with 4 bytes (BGRA) per pixel
                img = cv2.cvtColor(colorFrame, cv2.COLOR_BGRA2RGB)
                image = img[yPos * 2:yPos * 2 + yRes, xPos * 2:xPos * 2 + xRes].copy()

                new_frame_time = time.time()
                if self.res_s:
                    imageSave = image
                else:
                    imageSave = cv2.resize(image, (432, 368))
                imgSaveBGR = cv2.cvtColor(imageSave, cv2.COLOR_RGB2BGR)
                depthFrame = np.reshape(depthFrame, (424, 512))

                self.colorImage = image
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
                    selection = get_clickedtask(self)
                    saveFrames(imgSaveBGR, depthFrame, timestamp, self.colourfile, self.depthfile, self.paramFile,
                               selection)
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

    def onlineSim(self, progress_callback):
        while not self.newSes:
            if self.dataFlag == 1:
                try:
                    # poseImage = poseEST(self.colorImage)

                    h1, w1, ch = self.colorImage.shape
                    bytesPerLine = ch * w1

                    convertToQtFormat = QImage(self.colorImage.data.tobytes(), w1, h1, bytesPerLine,
                                               QImage.Format_RGB888)
                    p = convertToQtFormat.scaled(960, 540, Qt.KeepAspectRatio)
                    progress_callback.emit(p)
                    print("in loop")
                    # self.dataFlag = 0

                except:
                    pass

        if self.newSes:
            return p


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    # ImageUpdate()
    w.show()
    sys.exit(app.exec_())
