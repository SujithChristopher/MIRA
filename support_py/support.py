"""
Module with all the supporting classes and function for reading
and analysing Kinect data uisng OpenPose.

Author: Sivakumar Balasubramanian
Date: 04 Feb 2021
"""
import math
import os
import pickle
import sqlite3
import sys

import cv2
import numpy as np
import pandas as pd

import kinectmapper
from kinectmapper import PyKinectMapper


def read_pickle_file(fname):
    data = []
    with (open(fname, "rb")) as openfile:
        while True:
            try:
                data.append(pickle.load(openfile))
            except EOFError:
                break
    return data


class Params:
    root = 'C:\\Users\\CMC\\Documents\\LVS\\data'
    outdir = 'outdir'
    diag = 'diagdata'
    body = 'bodydata'
    otdata = '_mocap'

    PoseJoints = ("HEAD", "NECK", "RSHD", "RELB", "RWRT",
                  "LSHD", "LELB", "LWRT", "RHIP", "RKNE",
                  "RANK", "LHIP", "LKNE", "LANK",
                  "REYE", "REAR", "LEYE", "LEAR")
    ExtraPoseJoints = ("TRNK",)
    MaxHumans = 1
    PerfHeader = ("subj", "date", "time", "session", "rwrst5_x", "rwrst5_y",
                  "rwrst5_z", "rwrst50_x", "rwrst50_y",
                  "rwrst50_z", "rwrst95_x", "rwrst95_y",
                  "rwrst95_z", "lwrst5_x", "lwrst5_y",
                  "lwrst5_z", "lwrst50_x", "lwrst50_y",
                  "lwrst50_z", "lwrst95_x", "lwrst95_y",
                  "lwrst95_z", "trnkx5", "trnky5",
                  "trnkz5", "rsfe5", "lsfe5", "rsaa5",
                  "lsaa5", "refe5", "lefe5")

    @staticmethod
    def get_pose_header_for_col():
        # Genrate header for pose in color space.
        _head = [f"{_pj}_{_v}_{_nh}"
                 for _nh in range(Params.MaxHumans)
                 for _pj in Params.PoseJoints
                 for _v in ("x", "y", "s")]
        _head = _head + [f"{_pj}_{_v}_{_nh}"
                         for _nh in range(Params.MaxHumans)
                         for _pj in Params.ExtraPoseJoints
                         for _v in ("x", "y", "s")]
        return _head

    @staticmethod
    def get_pose_header_for_dep():
        # Genrate header for pose in depth space.
        _head = [f"{_pj}_{_v}_{_nh}"
                 for _nh in range(Params.MaxHumans)
                 for _pj in Params.PoseJoints
                 for _v in ("x", "y", "s")]
        _head = _head + [f"{_pj}_{_v}_{_nh}"
                         for _nh in range(Params.MaxHumans)
                         for _pj in Params.ExtraPoseJoints
                         for _v in ("x", "y", "s")]
        return _head

    @staticmethod
    def get_pose_header_for_cam():
        # Genrate header for pose camera space.
        return [f"{_pj}_{_v}_{_nh}"
                for _nh in range(Params.MaxHumans)
                for _pj in Params.PoseJoints
                for _v in ("x", "y", "z", "s")]

    @staticmethod
    def get_joint_angles_header():
        joints = ("TRNK_X", "TRNK_Y", "TRNK_Z", "RSHD_FE", "RSHD_AA",
                  "RELB_FE", "LSHD_FE", "LSHD_AA", "LELB_FE")
        return [f"{_pj}_{_nh}"
                for _nh in range(Params.MaxHumans)
                for _pj in joints]


def estimate_pose(coldata, pose_est):
    # Cycle through all the colorframe images and estimate pose.
    inx = 0
    N = len(coldata)
    humanpose = []
    while inx < N:
        # Read file.
        sys.stdout.write(f"\r{inx}")
        image = coldata[inx]
        h, w, _ = np.shape(image)

        # Estimate pose
        humans = pose_est.estimate_pose(image)
        humanpose.append(humans)
        inx += 1

    return humanpose


def map_pos_kinematics(coldata, depdata, humanpose, xoff=600, yoff=200):
    # Find the colorspace pixel positions for the different key points.
    poscol = []
    posdep = []
    poscam = []
    # Kinect mapper
    pyKinMapper = PyKinectMapper()
    # Width and height of image
    h, w, _ = coldata[0].shape
    Nj = len(Params.PoseJoints) + len(Params.ExtraPoseJoints)
    for i, _hp in enumerate(humanpose):
        sys.stdout.write(f"\r{i} ")
        # Depth frame 
        depthframe = depdata[i]
        # Initialize pose array
        _poscol = [None] * Nj
        _posdep = [None] * Nj
        _poscam = [None] * Nj
        if len(_hp) == 0:
            poscol.append(_poscol)
            posdep.append(_posdep)
            poscam.append(_poscam)
            continue

        # Update pose information
        # Pose joints
        for k, v in _hp[0].body_parts.items():
            _x = int(v.x * w * 2 + xoff)
            _y = int(v.y * h * 2 + yoff)

            _pd = pyKinMapper.get_depth_position(depthframe,
                                                 colspace_position=(_x, _y))
            _p3d = pyKinMapper.get_camspace_position(depthframe,
                                                     colspace_position=(_x, _y))
            _poscol[k] = {"x": _x, "y": _y, "s": v.score}
            _posdep[k] = {"x": _pd[0], "y": _pd[1]}
            _poscam[k] = {"x": _p3d[0], "y": _p3d[1], "z": _p3d[2]}

        # Extra pose joints
        # Computation will need to be done on a joint by joint basis.
        if (_poscol[2] != None and _poscol[5] != None):
            _x = int(0.5 * (_poscol[2]["x"] + _poscol[5]["x"]))
            _y = int(0.5 * (_poscol[2]["y"] + _poscol[5]["y"])) + 100
            _s = 0.5 * (_poscol[2]["s"] + _poscol[5]["s"])
            _pd = pyKinMapper.get_depth_position(depthframe,
                                                 colspace_position=(_x, _y))
            _p3d = pyKinMapper.get_camspace_position(depthframe,
                                                     colspace_position=(_x, _y))
            _poscol[18] = {"x": _x, "y": _y, "s": _s}
            _posdep[18] = {"x": _pd[0], "y": _pd[1]}
            _poscam[18] = {"x": _p3d[0], "y": _p3d[1], "z": _p3d[2]}
        else:
            _poscol[18] = None
            _posdep[18] = None
            _poscam[18] = None

        # Append pose data
        poscol.append(_poscol)
        posdep.append(_posdep)
        poscam.append(_poscam)
    return poscol, posdep, poscam


def get_poserow(hum, PoseJoints, ExtraPoseJoints):
    # Get pose for PoseJoints
    _rw = {}
    _nh = 0
    for _nj, _pj in enumerate(PoseJoints):
        # Make sure the human data is available
        if hum[_nj] != None:
            for _k, _v in hum[_nj].items():
                _rw[f"{_pj}_{_k}_{_nh}"] = _v
    # Add the trunk
    # Make sure the human data is available
    if hum[18] != None:
        for _k, _v in hum[18].items():
            _rw[f"TRNK_{_k}_{_nh}"] = _v
    return _rw


# Checks if a matrix is a valid rotation matrix.
def isRotationMatrix(R):
    Rt = np.transpose(R)
    shouldBeIdentity = np.dot(Rt, R)
    I = np.identity(3, dtype=R.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6


# Calculates rotation matrix to euler angles
# The result is the same as MATLAB except the order
# of the euler angles ( x and z are swapped ).
def rotationMatrixToEulerAngles(R):
    assert (isRotationMatrix(R))
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])

    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    return np.array([x, y, z])


def get_trunk_angle(camfdf):
    # Define trunk frame at each time instant.
    jnames = ["RSHD", "LSHD", "TRNK"]
    N = len(camfdf)
    _R = [None] * N
    _R0 = None
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # x axis
        _v1 = joints["LSHD"] - joints["RSHD"]
        _x = _v1 / np.linalg.norm(_v1, 2)
        _v2 = joints["TRNK"] - joints["RSHD"]
        _y = (_v2 - (_x.T @ _v2) * _x)
        _y = _y / np.linalg.norm(_y, 2)
        _z = np.array([np.cross(_x.T[0], _y.T[0])]).T
        _R[inx] = np.hstack([_x, _y, _z])
        # Assign initial trunk orientation.
        if _R0 is None and isRotationMatrix(_R[inx]):
            _R0 = _R[inx]
        # Compute turnk angle
        if _R0 is not None:
            _dR = _R0.T @ _R[inx]
            angles[inx] = (rotationMatrixToEulerAngles(_dR) * 180 / np.pi
                           if ~np.isnan(np.linalg.det(_dR)) else
                           [np.nan, np.nan, np.nan])
        else:
            angles[inx] = [np.nan, np.nan, np.nan]

    return np.array(angles)


def get_rightshoulder_rotmat(camfdf):
    # Define trunk frame at each time instant.
    jnames = ["RSHD", "LSHD", "TRNK"]
    N = len(camfdf)
    _R = [None] * N
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # x axis
        _v1 = joints["LSHD"] - joints["RSHD"]
        _x = _v1 / np.linalg.norm(_v1, 2)
        _v2 = joints["TRNK"] - joints["RSHD"]
        _y = (_v2 - (_x.T @ _v2) * _x)
        _y = _y / np.linalg.norm(_y, 2)
        _z = np.array([np.cross(_x.T[0], _y.T[0])]).T
        _R[inx] = np.hstack([_x, _y, _z])
    return np.array(_R)


def get_leftshoulder_rotmat(camfdf):
    # Define trunk frame at each time instant.
    jnames = ["RSHD", "LSHD", "TRNK"]
    N = len(camfdf)
    _R = [None] * N
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # x axis
        _v1 = joints["RSHD"] - joints["LSHD"]
        _x = _v1 / np.linalg.norm(_v1, 2)
        _v2 = joints["TRNK"] - joints["LSHD"]
        _y = (_v2 - (_x.T @ _v2) * _x)
        _y = _y / np.linalg.norm(_y, 2)
        _z = np.array([np.cross(_x.T[0], _y.T[0])]).T
        _R[inx] = np.hstack([_x, _y, _z])
    return np.array(_R)


def get_rightshoulder_angle(camfdf):
    jnames = ["RSHD", "RELB", "RWRT"]
    N = len(camfdf)
    rsh_rmat = get_rightshoulder_rotmat(camfdf)
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # upper-arm vector
        _rua = joints["RELB"] - joints["RSHD"]
        _ruaproj = rsh_rmat[inx].T @ _rua

        # Flexion-Extension angle
        _fe = np.arctan2(-_ruaproj[2, 0], _ruaproj[1, 0]) * 180 / np.pi
        # Abduction-Adduction angle
        _aa = np.arctan2(-_ruaproj[0, 0], _ruaproj[1, 0]) * 180 / np.pi
        angles[inx] = [_fe, _aa]
    return np.array(angles)


def get_leftshoulder_angle(camfdf):
    jnames = ["LSHD", "LELB", "LWRT"]
    N = len(camfdf)
    rsh_rmat = get_leftshoulder_rotmat(camfdf)
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # upper-arm vector
        _rua = joints["LELB"] - joints["LSHD"]
        _ruaproj = rsh_rmat[inx].T @ _rua
        # Flexion-Extension angle
        _fe = np.arctan2(_ruaproj[2, 0], _ruaproj[1, 0]) * 180 / np.pi
        # Abduction-Adduction angle
        _aa = np.arctan2(-_ruaproj[0, 0], _ruaproj[1, 0]) * 180 / np.pi
        angles[inx] = [_fe, _aa]
    return np.array(angles)


def get_rightelbow_angles(camfdf):
    jnames = ["RSHD", "RELB", "RWRT"]
    N = len(camfdf)
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # x axis
        _v1 = joints["RELB"] - joints["RSHD"]
        _v1 = _v1 / np.linalg.norm(_v1, ord=2)
        _v2 = joints["RWRT"] - joints["RELB"]
        _v2 = _v2 / np.linalg.norm(_v2, ord=2)
        angles[inx] = np.arccos((_v1.T @ _v2)[0, 0]) * 180 / np.pi
    return angles


def get_leftelbow_angles(camfdf):
    jnames = ["LSHD", "LELB", "LWRT"]
    N = len(camfdf)
    angles = [None] * N
    for inx in range(N):
        # Joint vectors
        joints = get_joint_vectors(camfdf, inx, jnames)
        # x axis
        _v1 = joints["LELB"] - joints["LSHD"]
        _v1 = _v1 / np.linalg.norm(_v1, ord=2)
        _v2 = joints["LWRT"] - joints["LELB"]
        _v2 = _v2 / np.linalg.norm(_v2, ord=2)
        angles[inx] = np.arccos((_v1.T @ _v2)[0, 0]) * 180 / np.pi
    return angles


def get_vector(df, inx, joint):
    return np.array([[df.loc[inx, f"{joint}_x_0"],
                      df.loc[inx, f"{joint}_y_0"],
                      df.loc[inx, f"{joint}_z_0"]]]).T


def get_joint_vectors(df, inx, joints):
    return {j: get_vector(df, inx, j) for j in joints}


def get_average_position(camfdf, joints=("RSHD", "LSHD", "NECK", "TRNK")):
    refpos = []
    N = len(camfdf)
    for inx in range(N):
        _jpos = get_joint_vectors(camfdf, inx, joints)
        refpos.append(np.mean([v for k, v in _jpos.items()
                               if np.isnan(np.sum(v)) == False], axis=0))
    return np.array(refpos)


def get_wrist_pos_wrt_ref(camfdf):
    # Reference position.
    refpos = get_average_position(camfdf, joints=("RSHD", "LSHD", "NECK"))
    rwrt_pos = []
    lwrt_pos = []
    N = len(camfdf)
    for inx in range(N):
        # Wrist position
        rwrt_pos.append(get_vector(camfdf, inx, "RWRT") - refpos[inx])
        lwrt_pos.append(get_vector(camfdf, inx, "LWRT") - refpos[inx])
    return np.array(rwrt_pos), np.array(lwrt_pos)


def get_performance_row(camfdf, trnk, rshd, lshd, relb, lelb):
    # Compute data summaries
    rwrt_pos, lwrt_pos = get_wrist_pos_wrt_ref(camfdf)
    # Endpoint space ROM
    r5, r50, r95 = [np.nanpercentile(rwrt_pos, q=q, axis=0)[:, 0]
                    for q in (5, 50, 95)]
    l5, l50, l95 = [np.nanpercentile(lwrt_pos, q=q, axis=0)[:, 0]
                    for q in (5, 50, 95)]
    # Trunk angles
    tx5, tx50, tx95 = [np.nanpercentile(trnk, q=q, axis=0)[0]
                       for q in (5, 50, 95)]
    ty5, ty50, ty95 = [np.nanpercentile(trnk, q=q, axis=0)[1]
                       for q in (5, 50, 95)]
    tz5, tz50, tz95 = [np.nanpercentile(trnk, q=q, axis=0)[2]
                       for q in (5, 50, 95)]

    # Shoulder angles
    rsfe5, rsfe50, rsfe95 = [np.nanpercentile(rshd, q=q, axis=0)[0]
                             for q in (5, 50, 95)]
    lsfe5, lsfe50, lsfe95 = [np.nanpercentile(lshd, q=q, axis=0)[0]
                             for q in (5, 50, 95)]
    # Shoulder angles
    rsaa5, rsaa50, rsaa95 = [np.nanpercentile(rshd, q=q, axis=0)[1]
                             for q in (5, 50, 95)]
    lsaa5, lsaa50, lsaa95 = [np.nanpercentile(lshd, q=q, axis=0)[1]
                             for q in (5, 50, 95)]

    # Elbow angles
    refe5, refe50, refe95 = [np.nanpercentile(relb, q=q, axis=0)
                             for q in (5, 50, 95)]
    lefe5, lefe50, lefe95 = [np.nanpercentile(lelb, q=q, axis=0)
                             for q in (5, 50, 95)]

    return {"rwrst5_x": r5[0],
            "rwrst5_y": r5[1],
            "rwrst5_z": r5[2],
            "rwrst50_x": r50[0],
            "rwrst50_y": r50[1],
            "rwrst50_z": r50[2],
            "rwrst95_x": r95[0],
            "rwrst95_y": r95[1],
            "rwrst95_z": r95[2],
            "lwrst5_x": l5[0],
            "lwrst5_y": l5[1],
            "lwrst5_z": l5[2],
            "lwrst50_x": l50[0],
            "lwrst50_y": l50[1],
            "lwrst50_z": l50[2],
            "lwrst95_x": l95[0],
            "lwrst95_y": l95[1],
            "lwrst95_z": l95[2],
            "trnkx5": tx5, "trnkx50": tx50, "trnkx95": tx95,
            "trnky5": ty5, "trnky50": ty50, "trnky95": ty95,
            "trnkz5": tz5, "trnkz50": tz50, "trnkz95": tz95,
            "rsfe5": rsfe5, "rsfe50": rsfe50, "rsfe95": rsfe95,
            "lsfe5": lsfe5, "lsfe50": lsfe50, "lsfe95": lsfe95,
            "rsaa5": rsaa5, "rsaa50": rsaa50, "rsaa95": rsaa95,
            "lsaa5": lsaa5, "lsaa50": lsaa50, "lsaa95": lsaa95,
            "refe5": refe5, "refe50": refe50, "refe95": refe95,
            "lefe5": lefe5, "lefe50": lefe50, "lefe95": lefe95}


"""
new functions added on 31-03-2021
"""


def get_clickedtask(self):
    if self.uns.isChecked():
        what_clicked = "UNS"  # Unspecified
    elif self.res.isChecked():
        what_clicked = "RES"  # rest
    elif self.txt.isChecked():
        what_clicked = "TXT"  # Texting
    elif self.fld.isChecked():
        what_clicked = "FLD"  # Folding
    elif self.but.isChecked():
        what_clicked = "BUT"  # buttoning
    elif self.bot.isChecked():
        what_clicked = "SRW"  # opening bottle
    elif self.brs.isChecked():
        what_clicked = "RNG"  # brushing
    elif self.cmb.isChecked():
        what_clicked = "CMB"  # combing
    elif self.eat.isChecked():
        what_clicked = "EAT"  # eating
    elif self.wrt.isChecked():
        what_clicked = "WRT"  # Writing
    elif self.drk.isChecked():
        what_clicked = "DRK"  # drinking
    elif self.phc.isChecked():
        what_clicked = "PHC"  # phone call
    elif self.wpt.isChecked():
        what_clicked = "WPT"  # wiping
    elif self.trn.isChecked():
        what_clicked = "TRN"  # Turn on switch
    elif self.wlk.isChecked():
        what_clicked = "WLK"  # walking
    elif self.zuz.isChecked():
        what_clicked = "ZUZ"  # Zipping and unzip
    elif self.eas.isChecked():
        what_clicked = "EAS"  # eating with spoon
    elif self.dwc.isChecked():
        what_clicked = "DWC"  # drink with tea cup
    elif self.tyh.isChecked():
        what_clicked = "TYH"  # tying hair
    elif self.tkm.isChecked():
        what_clicked = "TKM"  # Taking medicine
    elif self.snh.isChecked():
        what_clicked = "SNH"  # sanitize hands
    elif self.waf.isChecked():
        what_clicked = "WAF"  # washing face
    elif self.tyk.isChecked():
        what_clicked = "TYK"  # tying knot
    elif self.typ.isChecked():
        what_clicked = "TYP"  # typing from keyboard
    else:
        what_clicked = "UNS"

    return what_clicked


def get_calCalibData(self):
    """getting XYZ values for origin"""

    _originX = self.calibXYZrs[0][0]
    _originY = self.calibXYZrs[0][1]
    _originXr = list(range(_originX - 1, _originX + 2))
    _originYr = list(range(_originY - 1, _originY + 2))
    orgBox = []  # this takes a boundary of 3x3 pixel matrix

    for i in _originXr:
        for j in _originYr:
            pos = [i, j]
            orgBox.append(kinectmapper.PyKinectMapper().get_camspace_position(self.calibDepth, pos))
    orgData = pd.DataFrame(orgBox, columns=["X", "Y", "Z"])
    try:
        orgData.replace([np.inf, -np.inf], np.nan)
        orgData = orgData.mask(np.isinf(orgData))
        orgMean = orgData[["X", "Y", "Z"]].mean(skipna=True)
    except:
        pass

    # print(orgMean)

    """getting XYZ values for X plane"""

    _Xplanex = self.calibXYZrs[1][0]
    _Xplaney = self.calibXYZrs[1][1]
    _Xplanexr = list(range(_Xplanex - 1, _Xplanex + 2))
    _Xplaneyr = list(range(_Xplaney - 1, _Xplaney + 2))

    xPlaneBox = []
    for i in _Xplanexr:
        for j in _Xplaneyr:
            pos = [i, j]
            xPlaneBox.append(kinectmapper.PyKinectMapper().get_camspace_position(self.calibDepth, pos))

    xData = pd.DataFrame(xPlaneBox, columns=["X", "Y", "Z"])
    try:
        xData.replace([np.inf, -np.inf], np.nan)
        xData = xData.mask(np.isinf(xData))
        xPlaneMean = xData[["X", "Y", "Z"]].mean(skipna=True)
    except:
        pass

    # print(xPlaneMean)

    """getting XYZ values for Y plane"""

    _Yplanex = self.calibXYZrs[2][0]
    _Yplaney = self.calibXYZrs[2][1]
    _Yplanexr = list(range(_Yplanex - 1, _Yplanex + 2))
    _Yplaneyr = list(range(_Yplaney - 1, _Yplaney + 2))

    yPlaneBox = []
    for i in _Yplanexr:
        for j in _Yplaneyr:
            pos = [i, j]
            yPlaneBox.append(kinectmapper.PyKinectMapper().get_camspace_position(self.calibDepth, pos))

    yData = pd.DataFrame(yPlaneBox, columns=["X", "Y", "Z"])
    try:
        yData.replace([np.inf, -np.inf], np.nan)
        yData = yData.mask(np.isinf(yData))
        yPlaneMean = yData[["X", "Y", "Z"]].mean(skipna=True)
    except:
        pass

    # print(yPlaneMean)

    """ calculating vectors """

    v1 = xPlaneMean - orgMean
    v2 = yPlaneMean - orgMean

    _v1len = np.sqrt(v1.X * v1.X + v1.Y * v1.Y + v1.Z * v1.Z)
    v1norm = v1 / _v1len

    _ip12 = v1norm.X * v2.X + v1norm.Y * v2.Y + v1norm.Z * v2.Z * v2

    _err = v2 - _ip12 * v1norm
    _v2len = np.sqrt(_err.X * _err.X + _err.Y * _err.Y + _err.Z * _err.Z)
    v2norm = _err / _v2len
    xD = -v1norm["Y"] * v2norm["Z"] + v1norm["Z"] * v2norm["Y"]
    yD = -v1norm["Z"] * v2norm["X"] + v1norm["X"] * v2norm["Z"]
    zD = -v1norm["X"] * v2norm["Y"] + v1norm["Y"] * v2norm["X"]
    # print(xD)

    d = {"X": [xD],
         "Y": [yD],
         "Z": [zD]}

    v3norm = pd.DataFrame(data=d)
    # v11 = v1norm.to_numpy
    # print(v3norm['X'])

    rotMatrix = [[v1norm["X"], xD, v2norm["X"]],
                 [v1norm["Y"], yD, v2norm["Y"]],
                 [v1norm["Z"], zD, v2norm["Z"]]]
    print(rotMatrix)

    self.calibRotM = rotMatrix
    self.calibOrg = [orgMean["X"], orgMean["Y"], orgMean["Z"]]

    print("Calibrated")
    return self


def save_patient_details(self):
    pName = self.pName.text()
    pName = pName.upper()
    pMidName = self.pMidName.text()
    pMidName = pMidName.upper()
    pLastName = self.pLastName.text()
    pLastName = pLastName.upper()
    pLocality = self.pLocality.text()
    pCountry = self.pCountry.text()
    pState = self.pState.text()
    pCity = self.pCity.text()
    pAadhar = self.pAadhar.text()
    pPin = self.pPin.text()
    pPAN = self.pPAN.text()
    pAddress = self.pAddress.text()
    pMobile = self.pMobile.text()
    pEmail = self.pEmail.text()
    pDob = self.pDob.date().toString("ddMMyyyy")
    pTob = self.pTob.time().toString("HHmm")

    if self.pFemale.isChecked():
        pGen = "F"
    elif self.pMale.isChecked():
        pGen = "M"
    else:
        pGen = "U"

    if pLastName == "":
        pLastName = "XXXX"
    if pMidName == "":
        pMidName = "XXXX"
    if pCountry == "":
        pCountry = "XXX"
    if pPin == "":
        pPin = "XXXXXX"

    try:
        UIDname = pName[:4] + pMidName[:4] + pLastName[:4] + pGen + pDob + pTob + pCountry[:3] + pPin
        print(UIDname)

        self.pFileName = UIDname
        directory = UIDname
        parent_dir = self.data_path + "//splitVideos"

        if not os.path.exists(parent_dir):
            try:
                print(parent_dir)
                os.mkdir(parent_dir)
            except:
                pass
        path = os.path.join(parent_dir, directory)
        os.mkdir(path)

        fDetails = open(path + "//PATIENT_DETAILS.pickle", 'wb')
        _pDetails = [UIDname, pName, pMidName, pLastName, pDob, pTob, pGen, pLocality,
                     pCountry, pAddress, pEmail, pMobile, pAadhar, pPAN, pState, pCity, pPin]

        print(_pDetails)

        if self.profilePicture is not None:
            pickle.dump(self.profilePicture, fDetails)
            print("dumped")
        else:
            pic = cv2.imread(r"src\profilePicturePNG.png")
            pickle.dump(pic, fDetails)

        pickle.dump(_pDetails, fDetails)
        print("Dumped details")
        fDetails.close()
        self.statusBar().showMessage('Patient details are saved successfully, patient UID: ' + UIDname)

        db_update(self, _pDetails)
        db_fetch(self)
    except:
        pass


"""
database functions
"""


def db_create(self):
    """ this is for creating and new database and warning old data will be lost"""

    pth = self.data_path
    if not os.path.exists(f"{pth}//patient_db.db"):
        self.conn = sqlite3.connect(f"{pth}//patient_db.db")
        self.pc = self.conn.cursor()
        self.pc.execute("""CREATE TABLE patient(uid type TEXT, 
                            f_name type TEXT, m_name type TEXT, l_name type TEXT, 
                            pDob type TEXT, pTobtype type TEXT, pGen type TEXT, pLocality type TEXT,
                            pCountry type TEXT, pAddress type TEXT, pEmail type TEXT, 
                            pMobile type TEXT, pAadhar type TEXT, pPAN type TEXT, 
                            pState type TEXT, pCity type TEXT, pPin type TEXT                          
                            )""")
        print("patient database created")
    else:
        self.conn = sqlite3.connect(f"{pth}//patient_db.db")
        self.pc = self.conn.cursor()
        print("Existing database found")

    if not os.path.exists(f"{pth}//session_db.db"):
        self.sconn = sqlite3.connect(f"{pth}//session_db.db")
        self.sc = self.sconn.cursor()
        print("session database created")
    else:
        self.sconn = sqlite3.connect(f"{pth}//session_db.db")
        self.sc = self.sconn.cursor()
        print("Session database found")
    db_fetch(self)


def db_update(self, db_data):
    """INSERTING NEW patient data"""
    print(self.pc.lastrowid)
    self.pc.execute("""INSERT INTO patient(uid, f_name, m_name, l_name, 
                            pDob, pTobtype, pGen, pLocality,pCountry, pAddress, pEmail, 
                            pMobile, pAadhar, pPAN, pState, pCity, pPin) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", db_data)
    self.conn.commit()
    self.pc.execute("SELECT * FROM patient ORDER BY rowid")
    db_sestable_create(self, db_data[0])
    print("done")

    # print("database values", self.pc.fetchall())


def db_fetch(self):
    self.p_list_wid.clear()
    self.pc.execute("""SELECT rowid, f_name, l_name, uid FROM patient ORDER BY rowid""")
    self.p_list = self.pc.fetchall()
    newlist = []
    for ls in self.p_list:
        newlist.append(str(ls[1] + " " + ls[2]))
    print(newlist)
    self.p_list_wid.addItems(newlist)


def db_p_select(self, row):
    self.pc.execute("""SELECT rowid, uid FROM patient ORDER BY rowid""")
    s = self.pc.fetchall()
    sel = s[row]
    s_uid = sel[1]
    print("this is uid", s_uid)
    self.selected_p = s_uid
    db_ses_fetch(self, s_uid)


def db_sestable_create(self, uid):
    self.sc.execute(f"CREATE TABLE {uid}(session text, analyse boolean, extra boolean)")
    self.sconn.commit()
    print("session created")


def db_ses_fetch(self, uid):
    self.p_ses_wid.clear()
    self.sc.execute(f"SELECT * FROM {uid} ORDER BY rowid")
    self.ses_list = self.sc.fetchall()
    print("this is list of sessions", self.ses_list)

    sql_query = """SELECT name FROM sqlite_master  
      WHERE type='table';"""

    self.sc.execute(sql_query)
    print("listing everything", self.sc.fetchall())
    newlist = []
    for ls in self.ses_list:
        newlist.append(str(ls[0]))
    print(newlist)

    self.ses_list = newlist
    self.p_ses_wid.addItems(newlist)


def db_ses_update(self, uid, ses_name, analyse=False, extra=False):
    datals = [ses_name, analyse, extra]
    self.sc.execute(f"INSERT INTO {uid}(session, analyse, extra) VALUES (?,?,?)", datals)
    print(f"INSERT INTO {uid}({ses_name})")
    self.sconn.commit()
    print("session saved")
    db_fetch(self)



def db_remove_all(self, row):
    self.pc.execute("DELETE FROM patient *")
    self.conn.commit()
