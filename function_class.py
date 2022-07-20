import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *
from guiDesign import Ui_MainWindow

import os
import sys
import pickle

"""importing database functions"""
from support_py.support import db_create
from support_py.support import db_ses_fetch
from support_py.support import db_ses_update
from support_py.support import db_fetch
from support_py.support import db_remove_all
from support_py.support import db_p_select
from support_py.support import save_patient_details

from support_py.support import get_calCalibData
from support_py.support import get_clickedtask


class Mira_functions(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(Mira_functions, self).__init__(*args, **kwargs)
        self.selected_camera = None

    def save_frame_fun(self):
        pass

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
        # sys.exit(app.exec_())
        pass

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

    """ second tab save frames """

    def save_current_frame(self):
        if self.sessionDir == "" or self.sessionDir is None:
            print("please select the patient directory")

        else:
            _frame_pth = os.path.join(self.sessionDir, "FRAME_", self.session)



