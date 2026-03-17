# -*- coding: utf-8 -*-

#import time
import random

import numpy as np
import urllib2
from pyfirmata import Arduino, util

time=util.time

board = Arduino('COM14', baudrate=57600)#, baudrate=9600
it = util.Iterator(board)
it.start()
board.analog[0].enable_reporting()
pin8 = board.get_pin('d:8:o')
pin9 = board.get_pin('d:9:o')
pin10 = board.get_pin('d:10:o')
pin11 = board.get_pin('d:11:o')
servo1=board.get_pin('d:5:s')
servo2=board.get_pin('d:6:s')
echo_pin = board.get_pin('d:7:o')


def ping(n):
    "Повертає середнє значення відстані, виміряної ультразвуковим сенсором, n - кількість вимірювань"
    return sum([util.ping_time_to_distance(echo_pin.ping()) for i in [0]*n])/n

def scan():
    angle=0
    X=[]
    Y=[]
    while angle<=130:
        servo1.write(angle)
        time.sleep(1)
        dist=ping(3)
        X.append(angle)
        Y.append(dist)
        print board.analog[0].read()
        angle+=13
    return X,Y

def scan3D():
    H,V,D=[],[],[]
    for v in [130, 70]: # скануємо знизу і зверху
        servo2.write(v) # 70-130
        #board.pass_time(0.1)
        time.sleep(0.05)
        h=0
        while h<=130:
            servo1.write(h)
            time.sleep(0.1)
            d=ping(1)
            H.append(h)
            V.append(v)
            D.append(int(d<40 and d!=0))
            #print h,v,d
            #print board.analog[0].read(),
            h+=13
    return H,V,D

def stop(t=0):
    pin8.write(0)
    pin9.write(0)
    pin10.write(0)
    pin11.write(0)
    if t: time.sleep(t)

def RF(t, s=True):
    pin10.write(0)
    pin11.write(1)
    time.sleep(t)
    if s: stop()

def RB(t):
    pin10.write(1)
    pin11.write(0)
    time.sleep(t)
    stop()

def LF(t):
    pin8.write(0)
    pin9.write(1)
    time.sleep(t)
    stop()

def LB(t):
    pin8.write(1)
    pin9.write(0)
    time.sleep(t)
    stop()

def F(t):
    RF(0.1, False)
    LF(t)
    stop()

def B(t):
    RB(0.1)
    LB(t)
    stop()

def getXY():
    response = urllib2.urlopen('http://192.168.0.101/')
    data=response.read()
    response.close()
    if not data:
        time.sleep(2)
        return None
    x1,y1,x2,y2=[int(x) for x in data.split()]
    return x1,y1,x2,y2

def inCircle(x,y,cx,cy,r):
    if (x - cx)**2 + (y - cy)**2 < r**2:
        return True
    return False

def dist(x1,y1,x2,y2):
    return ((x2 - x1)**2 +(y2 - y1)**2)**0.5

while True:
    data=getXY()
    if not data: continue
    x1,y1,x2,y2=data
    d1=dist(x1,y1,x2,y2)
    F(1)
    data=getXY()
    if not data: continue
    x1,y1,x2,y2=data
    d2=dist(x1,y1,x2,y2)
    if d2>d1:
        R(1)
    else:
        F(1)
    time.sleep(2)

board.exit()
