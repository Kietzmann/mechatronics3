# -*- coding: utf-8 -*-

import random

from pyfirmata import Arduino, util

time=util.time
board = Arduino('COM7', baudrate=57600)#, baudrate=9600
print board
it = util.Iterator(board)
it.start()
#board.analog[0].enable_reporting()
pin8 = board.get_pin('d:8:o')
pin9 = board.get_pin('d:9:o')
pin10 = board.get_pin('d:10:o')
pin11 = board.get_pin('d:11:o')
servo1=board.get_pin('d:5:s')
servo2=board.get_pin('d:6:s')
echo_pin = board.get_pin('d:7:o')
autho=True

def ping(n):
    "Повертає середнє значення відстані, виміряної ультразвуковим сенсором, n - кількість вимірювань"
    return sum([util.ping_time_to_distance(echo_pin.ping()) for i in [0]*n])/n

def scan():
    servo2.write(70) # 70-130
    angle=0
    X=[]
    Y=[]
    while angle<=130:
        servo1.write(angle)
        time.sleep(0.9)
        dist=ping(3)
        print angle, dist
        X.append(angle)
        #Y.append(dist)
        Y.append(int(dist<40 and dist!=0))
        #print board.analog[0].read()
        angle+=13
        root.update_idletasks()
        root.update()
    return X,Y

def stop(t=0):
    pin8.write(0)
    pin9.write(0)
    pin10.write(0)
    pin11.write(0)
    if t: time.sleep(t)

def LF(t, s=True):
    pin10.write(0)
    pin11.write(1)
    time.sleep(t)
    if s: stop()

def LB(t, s=True):
    pin10.write(1)
    pin11.write(0)
    time.sleep(t)
    if s: stop()

def RF(t, s=True):
    pin8.write(0)
    pin9.write(1)
    time.sleep(t)
    if s: stop()

def RB(t, s=True):
    pin8.write(1)
    pin9.write(0)
    time.sleep(t)
    if s: stop()

def F(t, s=True):
    RF(0.01, False)
    LF(t)
    if s: stop()

def B(t, s=True):
    RB(0.01, False)
    LB(t)
    if s: stop()

def Rot(angle, ar):
    # розвернутись на кут
    k=0.01 # емпіричний коефіцієнт
    if (0<=angle<=ar/2.):
        LF(angle*k) # ліворуч
    elif (ar/2.<angle<=ar):
        RF((angle-ar/2.)*k) # праворуч

def opt_angle(X,Y):
    """Оптимальний кут повороту за результатами сканування"""
    angles=[] # оптимальні напрямки
    for x,y in zip(X,Y): # для усіх результатів сканування
        if y: # якщо в цьому напрямку щось є
            angles.append(x) # то додати до оптимальних кутів
    #angle=random.choice(angles) # вибрати випадковий напрямок
    angle=angles[len(angles)//2] # середній
    return angle

def strategy(i=0):
    """Стратегія робота"""
    X,Y=scan() # сканує
    visualize(Y)
    print X
    print Y
    if any(Y): # якщо щось знайдено
        angle=opt_angle(X,Y)
        print "angle=", angle
        Rot(angle, 130) # повернутись до об'єкта
        if i==1:
            F(2) # штовхати прямо
            B(2) # повернутись назад
        else:
            strategy(1) # рекурсія?
    else: # якщо не знайдено
        angle=180*random.random() # випадковий напрямок
        Rot(angle, 180) # повернутись
        F(0.1) # іхати прямо
        #strategy() # рекурсія?

def update():
    """Викликається кожну секунду"""
    strategy()
    if autho: root.after(1000, update)

def key_handler(event=None):
    global autho
    s=None
    if event:
        k=event.keycode
        print "keycode=",k
        if   k==39: s=RF # <вправо>
        elif k==37: s=LF # <вліво>
        elif k==40: s=B # <вниз>
        elif k==38: s=F # <вверх>
        elif k==34: servo1.write(servo1.value-10) # <PageDown>
        elif k==33: servo1.write(servo1.value+10) # <PageUp>
        elif k==36: servo2.write(servo2.value-10) # <Home>
        elif k==35: servo2.write(servo2.value+10) # <End>
        elif k==32: time.sleep(5) # <Space>
        elif k==80: autho=False # <P>
        elif k==83: autho=True; update() # <S>
        elif k==27: stop(); board.exit(); r.destroy() # вихід <Esc>
        else: s=None
        time.sleep(0.1)
        if s:
            s(0.2)
            time.sleep(0.1)
            print s.__name__

# while True:
#     ball.draw()
#     tk.update_idletasks()
#     tk.update()

class Evnt:
    def __init__(self, keycode):
        self.keycode=keycode

def button(text, keycode, relx, rely):
    btn=tk.Button(root, text=text, command=lambda: key_handler(Evnt(keycode)))
    btn.place(relx=relx, rely=rely, relwidth=0.3, relheight=0.1)

canvas_width = 100
canvas_height = 100
def visualize(sensor_data = [30, 50, 20, 40, 10, 35, 45]):
    scale_factor = canvas_height / (max(sensor_data)+1)
    canvas.delete("all")
    for i, distance in enumerate(sensor_data):
        # Calculate the x-coordinates for the bar
        x1 = i * (canvas_width / len(sensor_data))
        x2 = (i + 1) * (canvas_width / len(sensor_data))

        # Calculate the y-coordinates for the bar
        y1 = canvas_height
        y2 = canvas_height - (distance * scale_factor)

        # Draw the bar on the canvas
        canvas.create_rectangle(x1, y1, x2, y2, fill="blue")

if __name__=="__main__":
    import Tkinter as tk
    root = tk.Tk()
    button("^", 38, 0.3, 0.0)
    button("<", 37, 0.0, 0.1)
    button(">", 39, 0.6, 0.1)
    button("v", 40, 0.3, 0.2)
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.place(relx=0, rely=0.3, relwidth=1, relheight=0.7)
    root.bind('<Key>', key_handler)
    root.after(0, update)  # begin updates
    root.mainloop()
    stop()
    board.exit()
