from PyQt5.QtGui import *


def calibrate_using_clicked_points(self, img):

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

        return p
    

