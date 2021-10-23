"""Module to handle kinect related mapping operations.

Author: Sivakumar Balasubramanian
Date: 05 Feb 2021
"""

import numpy as np
import ctypes
from pykinect2 import PyKinectV2 as PK2
from pykinect2 import PyKinectRuntime as PKrt


class PyKinectMapper():
    """
    Class to handle data mapping operations with the Kinect.
    """
    colShape = (1080, 1920)
    depShape = (424, 512)
    colSz = np.int(np.prod(colShape))
    depSz = np.int(np.prod(depShape))

    def __init__(self):
        _flag = (PK2.FrameSourceTypes_Color |
                 PK2.FrameSourceTypes_Depth)
        self._kinect = PKrt.PyKinectRuntime(_flag)
    
        # For camera space position
        TYPE_CameraSpacePointArray = (PK2._CameraSpacePoint *
                                      PyKinectMapper.colSz)
        self._camspcPtr = TYPE_CameraSpacePointArray()
        # For depth space position.
        color2depth_points_type = PK2._DepthSpacePoint * PyKinectMapper.colSz
        self._color2depth_points = ctypes.cast(color2depth_points_type(),
                                               ctypes.POINTER(PK2._DepthSpacePoint))

    def get_camspace_position(self, depthframe, colspace_position):
        """
        Returns the camera space position for the given color space position
        using the input depth-frame.
        """
        # Defines to allow colour pixel mapping to 3D coords to work correctly     
        ctypes_depth_frame = np.ctypeslib.as_ctypes(depthframe.flatten())
        depSz = depthframe.size
        self._kinect._mapper.MapColorFrameToCameraSpace(depSz,
                                        ctypes_depth_frame,
                                        PyKinectMapper.colSz,
                                        self._camspcPtr)
        
        # Find 3D position of each pixel (relative to camera) using 
        # Colour_to_camera method, all measurements (x, y and z) in m
        _inx = PyKinectMapper.get_colorspace_index(xpos=colspace_position[0],
                                                   ypos=colspace_position[1])
        return [self._camspcPtr[_inx].x,
                self._camspcPtr[_inx].y,
                self._camspcPtr[_inx].z]
    
    def get_depth_position(self, depthframe, colspace_position):
        """Returns the depth space position data for the given color space
        position using the input depthframe.
        """
        # Defines to allow colour pixel mapping to 3D coords to work correctly     
        ctypes_depth_frame = np.ctypeslib.as_ctypes(depthframe.flatten())
        depSz = depthframe.size
        # Note the method on the line below, for finding the corresponding depth
        # pixel of a single tracked pixel in the colour image, is NOT what I
        # am using to find the 3D position of a colour pixel
        self._kinect._mapper.MapColorFrameToDepthSpace(
                                ctypes.c_uint(PyKinectMapper.depSz), ctypes_depth_frame,
                                ctypes.c_uint(PyKinectMapper.colSz),
                                self._color2depth_points)
        
        # Method below finds 2D depth pixel that corresponds to a 2D colour
        # pixel, for use in the pop up images, to show you what points you are
        # tracking. While it could be used to find 3D joint positions, IT IS
        # NOT THE METHOD I USE OR RECOMMEND FOR FINDING 3D JOINT POSITIONS,
        # as it gives you x and y in pixels not m (z is in mm)
        _inx = PyKinectMapper.get_colorspace_index(xpos=colspace_position[0],
                                                   ypos=colspace_position[1])
        _x = self._color2depth_points[_inx].x
        _x = 0 if np.isinf(_x) else int(_x)
        _y = self._color2depth_points[_inx].y
        _y = 0 if np.isinf(_y) else int(_y)
        return [_x, _y]

    @staticmethod
    def get_colorspace_index(xpos, ypos):
        """
        Retuns the index position in the array for the given x and y pixel
        positions.
        """
        return ypos * PyKinectMapper.colShape[1] + xpos