from PyQt5.QtMultimedia import QMediaPlayer


def initialize_buttons(self):
    self.displayLabel.mousePressEvent = self.updateRect
    self.task_group.hide()
    self.task_group.mousePressEvent = self.select_task

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
    self.selectXYZ.clicked.connect(self.select_fun)
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

    #camera list widget
    self.camera_list.itemClicked.connect(self.camera_list_clicked)

    """frame tab"""
    # self.capture_frame.clicked.connect(self.capture_frame_fun)
    self.frame_display.mousePressEvent = self.updateRect

