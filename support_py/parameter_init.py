from PyQt5.QtGui import *


def initialize_parameters(self):
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

    self.profilePicture = None

    self.calibCounter = 0
    self.calibXYZ = []
    self.calibXYZrs = []

    self.globDate = self.dateEdit.date()
    self.statusBar().showMessage("Initialized")
    self.statusBar().setFont(QFont('Times', 12))

    """
    Fixed roi parameters
    """
    self.fx_roi = False
    self.imu_trigger = True

def camera_list_init(self):
    
    self.camera_list.addItems(self.device_list)


