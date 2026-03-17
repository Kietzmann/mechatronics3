# Hardware setup

This guide describes the physical wiring between the Arduino and the robot's
motors, servos, and ultrasonic sensor.

## Bill of materials

| Qty | Component | Notes |
|---|---|---|
| 1 | Arduino Uno (or Mega / Nano) | Any pyFirmata-compatible board |
| 1 | L298N dual H-bridge motor driver | Powers the two DC motors |
| 2 | DC gear motors + wheels | Included in most 2WD chassis kits |
| 1 | Caster wheel | Rear support (ball or swivel) |
| 2 | SG90 micro-servos | Horizontal pan + vertical tilt |
| 1 | HC-SR04 ultrasonic sensor | Mounted on the servo bracket |
| 1 | 2WD robot chassis | Acrylic or 3D-printed platform |
| 1 | Battery holder (4xAA or 7.4 V Li-Po) | Motor power supply |
| 1 | USB cable (or HC-05 Bluetooth module) | Serial link to the laptop |

A ready-made kit such as the one linked in the original project description
contains all of the above.

## Firmware

Upload **StandardFirmata** to the Arduino before first use:

1. Open the Arduino IDE.
2. Go to **File > Examples > Firmata > StandardFirmata**.
3. Select your board type and serial port under **Tools**.
4. Click **Upload**.

mechatronics3 communicates with the board through the Firmata protocol via
pyFirmata. No custom Arduino sketch is required.

## Default pin mapping

The default pin assignments match the original ArduinoRoboCar wiring and are
defined in `src/mechatronics3/config.py` (`PinMap` class).

| Function | Arduino pin | Config key |
|---|---|---|
| Left motor — forward | D9 | `MECH_PINS__MOTOR_LEFT_FWD` |
| Left motor — backward | D8 | `MECH_PINS__MOTOR_LEFT_BWD` |
| Right motor — forward | D11 | `MECH_PINS__MOTOR_RIGHT_FWD` |
| Right motor — backward | D10 | `MECH_PINS__MOTOR_RIGHT_BWD` |
| Horizontal servo (pan) | D5 | `MECH_PINS__SERVO_HORIZONTAL` |
| Vertical servo (tilt) | D6 | `MECH_PINS__SERVO_VERTICAL` |
| Ultrasonic echo | D7 | `MECH_PINS__ECHO` |

All pin numbers can be overridden via environment variables or a `.env` file.

## Wiring diagram

```
                ┌──────────────────────┐
                │      Arduino Uno     │
                │                      │
    USB ────────┤ USB            D5  ──┼──── Horizontal servo signal
                │                D6  ──┼──── Vertical servo signal
                │                D7  ──┼──── HC-SR04 echo
                │                D8  ──┼──── L298N IN1 (left motor bwd)
                │                D9  ──┼──── L298N IN2 (left motor fwd)
                │                D10 ──┼──── L298N IN3 (right motor bwd)
                │                D11 ──┼──── L298N IN4 (right motor fwd)
                │                      │
                │                5V  ──┼──── Servo VCC, HC-SR04 VCC
                │                GND ──┼──── Common ground
                └──────────────────────┘

    L298N motor driver
    ───────────────────
    IN1 ← D8    IN2 ← D9     (left motor)
    IN3 ← D10   IN4 ← D11    (right motor)
    12V ← battery +
    GND ← battery − & Arduino GND
    OUT1/OUT2 → left motor terminals
    OUT3/OUT4 → right motor terminals

    HC-SR04
    ────────
    VCC  → 5 V
    Trig → (directly from echo pin via Firmata ping)
    Echo → D7
    GND  → GND

    Servos (SG90)
    ──────────────
    Signal → D5 (horizontal) / D6 (vertical)
    VCC    → 5 V (or external 5 V supply for high-torque servos)
    GND    → GND
```

### Motor direction convention

The `MotorController` uses the following logic for each motor:

| Movement | Left fwd (D9) | Left bwd (D8) | Right fwd (D11) | Right bwd (D10) |
|---|---|---|---|---|
| Forward | 1 | 0 | 1 | 0 |
| Backward | 0 | 1 | 0 | 1 |
| Left forward | 1 | 0 | 0 | 0 |
| Right forward | 0 | 0 | 1 | 0 |
| Left backward | 0 | 1 | 0 | 0 |
| Right backward | 0 | 0 | 0 | 1 |
| Stop | 0 | 0 | 0 | 0 |

The `forward()` method applies a 100 ms lead-in on the right motor to
compensate for uneven torque — tune this if your chassis pulls to one side.

### Servo range

Both servos accept angles from 0 to 180 degrees. The `center()` method
defaults to 65° horizontal and 90° vertical. The ultrasonic scan sweeps
the horizontal servo from 0° to 130° in 13° steps.

## Sensor mounting

Mount the HC-SR04 ultrasonic sensor on the servo bracket so the horizontal
servo pans left/right and the vertical servo tilts up/down. This allows the
`scan_3d()` method to build a two-axis detection grid.

Typical scan parameters (configurable via `MECH_SCAN__*` environment
variables):

| Parameter | Default | Description |
|---|---|---|
| `angle_min` | 0 | Start of horizontal sweep (degrees) |
| `angle_max` | 130 | End of horizontal sweep (degrees) |
| `angle_step` | 13 | Degrees between measurements |
| `vertical_angles` | 110, 60 | Vertical positions for 3-D scan |
| `distance_threshold` | 40.0 | Distance (cm) below which an object is flagged |
| `ping_samples` | 3 | Readings averaged per measurement |

## Supported boards

mechatronics3 uses pyFirmata, which supports any board running StandardFirmata:

- Arduino Uno
- Arduino Mega 2560
- Arduino Nano
- Arduino Leonardo

Other Firmata-compatible boards (e.g. ESP32 with ConfigurableFirmata) may work
but are untested.

## Power considerations

- The L298N module needs an external power supply (7–12 V) for the motors.
  Do not power motors from the Arduino 5 V pin.
- SG90 servos draw up to ~750 mA under load. If both servos stall
  simultaneously, use a separate 5 V regulator rather than the Arduino's
  on-board regulator.
- The HC-SR04 draws ~15 mA and can be powered from the Arduino 5 V pin.

## Wireless operation

To operate the robot without a USB tether, replace the USB cable with a
Bluetooth serial module (e.g. HC-05):

1. Wire the HC-05 TX → Arduino RX and HC-05 RX → Arduino TX.
2. Pair the module with your laptop.
3. Set `MECH_SERIAL_PORT` to the Bluetooth serial device
   (e.g. `/dev/rfcomm0` on Linux or `COM5` on Windows).
4. The baud rate must match the HC-05 configuration (default 57600).
