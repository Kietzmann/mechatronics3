# -*- coding: utf-8 -*-

#import time
import random

import numpy as np
from pyfirmata import Arduino, util
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split

time=util.time
board = Arduino('COM25')
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
    for v in [110, 60]: # скануємо знизу і зверху
        h=0
        while h<=130:
            servo2.write(v) # 70-130
            time.sleep(0.01)
            servo1.write(h)
            time.sleep(1)
            d=ping(3)
            H.append(h)
            V.append(v)
            D.append(int(d<40 and d!=0))
            #print h,v,d
            #print board.analog[0].read(),
            h+=13
    return H,V,D

"""
import numpy as np
from scipy.optimize import curve_fit
X,Y=scan()
print X,Y
X=np.array(X)
Y=np.array(Y)
def f(x, a, b):
    return a*x**2+b
popt, pcov = curve_fit(f, X, Y)
R2=np.corrcoef(Y, f(X,*popt))[0,1]**2
if R2>0.5:
     print X[np.argmin(f(X,*popt))]
"""

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

# деякі дані для навчання - об'єкт шириною 10 см, висотою 10 см
x=np.array([
[1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

[1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0,  1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
[0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0,  0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0],
[0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0,  0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0],
[0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0,  0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
[0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0,  0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
[0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0,  0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0],
[0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0,  0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0,  0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
[0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1,  0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1],

[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
])

y=np.array([1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0])

x_train, x_test, y_train, y_test = train_test_split(x,y,test_size=0.1)
model=GradientBoostingClassifier(n_estimators=10, learning_rate=0.1, max_depth=3) # модель
model.fit(x_train, y_train) # виконати навчання
print y_test # фактичні тестові класи
print model.predict(x_test) # прогнозовані тестові класи
print model.score(x_test, y_test) # правильність класифікатора

# перехресна перевірка (удосконалення train_test_split + score)
from sklearn.model_selection import cross_val_score

s=cross_val_score(model, x, y, cv=9)
print s, s.mean() # правильність класифікатора на кожній ітерації і її середнє значення
print model.predict([[0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1,  0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])

while True:
    H,V,D=scan3D()
    p=model.predict(np.array(D).reshape(1,-1))[0] # клас: 1 - є об'єкт, 0 - немає
    if p: # якщо об'єкт ідентифіковано
        F(5) # штовхати!
    else:
        # інакше рухатись випадково
        direction=random.choice([F,LF,RF])
        direction(random.random())

board.exit()
