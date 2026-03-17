# -*- coding: utf-8 -*-
import cv2
import numpy as np
from bottle import WSGIRefServer, request, route, run


def detectColor(h1, s1, v1, h2, s2, v2):
    h_min = np.array((h1, s1, v1), np.uint8)
    h_max = np.array((h2, s2, v2), np.uint8)
    RealTimeMask = cv2.inRange(frame_hsv, h_min, h_max)
    moments = cv2.moments(RealTimeMask, 1)
    dM01 = moments["m01"]
    dM10 = moments["m10"]
    Area = moments["m00"]
    # print Area
    if Area:
        x = int(dM10 / Area)
        y = int(dM01 / Area)
        cv2.circle(frame, (x, y), 10, (0, 0, 255), -1)
        return x, y, RealTimeMask
    else:
        return None, None, RealTimeMask


cap = cv2.VideoCapture(0)
frame = None
frame_hsv = None


def getXY():
    global frame, frame_hsv
    ret, frame = cap.read()
    frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    x1, y1, RealTimeMask = detectColor(159, 39, 103, 180, 255, 255)
    x2, y2, RealTimeMask = detectColor(25, 70, 159, 55, 162, 255)
    if all([x1, y1, x2, y2]):
        return "%i %i %i %i" % (x1, y1, x2, y2)
    return ""


@route("/")  # http://localhost:80
def index():
    return getXY()


run(server=WSGIRefServer, host="192.168.0.101", port=80)
cap.release()
cv2.destroyAllWindows()
