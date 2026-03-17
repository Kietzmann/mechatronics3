"""Tests for MotorController — verify correct pin write sequences."""

from __future__ import annotations

from unittest.mock import patch

from mechatronics3.core.motor import MotorController


class TestStop:
    def test_stop_clears_all_pins(self, motor: MotorController) -> None:
        motor._lf.write(1)
        motor._rb.write(1)
        motor.stop()
        assert motor._lf.read() == 0
        assert motor._lb.read() == 0
        assert motor._rf.read() == 0
        assert motor._rb.read() == 0


class TestRightForward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_sets_rf_high_rb_low(self, _sleep, motor: MotorController) -> None:
        motor.right_forward(0.5)
        assert motor._rf.read() == 0  # auto-stop clears it
        assert motor._rb.read() == 0

    @patch("mechatronics3.core.motor.time.sleep")
    def test_no_auto_stop(self, _sleep, motor: MotorController) -> None:
        motor.right_forward(0.5, auto_stop=False)
        assert motor._rf.read() == 1
        assert motor._rb.read() == 0


class TestRightBackward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_sets_rb_high_rf_low(self, _sleep, motor: MotorController) -> None:
        motor.right_backward(0.5)
        assert motor._rf.read() == 0
        assert motor._rb.read() == 0  # auto-stop

    @patch("mechatronics3.core.motor.time.sleep")
    def test_no_auto_stop(self, _sleep, motor: MotorController) -> None:
        motor.right_backward(0.5, auto_stop=False)
        assert motor._rb.read() == 1
        assert motor._rf.read() == 0


class TestLeftForward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_sets_lf_high_lb_low(self, _sleep, motor: MotorController) -> None:
        motor.left_forward(0.5)
        assert motor._lf.read() == 0  # auto-stop
        assert motor._lb.read() == 0

    @patch("mechatronics3.core.motor.time.sleep")
    def test_no_auto_stop(self, _sleep, motor: MotorController) -> None:
        motor.left_forward(0.5, auto_stop=False)
        assert motor._lf.read() == 1
        assert motor._lb.read() == 0


class TestLeftBackward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_sets_lb_high_lf_low(self, _sleep, motor: MotorController) -> None:
        motor.left_backward(0.5)
        assert motor._lb.read() == 0  # auto-stop
        assert motor._lf.read() == 0

    @patch("mechatronics3.core.motor.time.sleep")
    def test_no_auto_stop(self, _sleep, motor: MotorController) -> None:
        motor.left_backward(0.5, auto_stop=False)
        assert motor._lb.read() == 1
        assert motor._lf.read() == 0


class TestForward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_forward_activates_both_motors(self, _sleep, motor: MotorController) -> None:
        motor.forward(1.0)
        assert motor._rf.read() == 0
        assert motor._lf.read() == 0


class TestBackward:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_backward_activates_both_motors(self, _sleep, motor: MotorController) -> None:
        motor.backward(1.0)
        assert motor._rb.read() == 0
        assert motor._lb.read() == 0


class TestRotate:
    @patch("mechatronics3.core.motor.time.sleep")
    def test_rotate_left_half(self, _sleep, motor: MotorController) -> None:
        motor.rotate(30.0, angle_range=130.0)
        assert motor._lf.read() == 0  # auto-stop after left_forward

    @patch("mechatronics3.core.motor.time.sleep")
    def test_rotate_right_half(self, _sleep, motor: MotorController) -> None:
        motor.rotate(100.0, angle_range=130.0)
        assert motor._rf.read() == 0  # auto-stop after right_forward

    @patch("mechatronics3.core.motor.time.sleep")
    def test_rotate_at_midpoint_goes_left(self, _sleep, motor: MotorController) -> None:
        motor.rotate(65.0, angle_range=130.0)
        assert motor._lf.read() == 0

    @patch("mechatronics3.core.motor.time.sleep")
    def test_rotate_beyond_range_does_nothing(self, _sleep, motor: MotorController) -> None:
        motor.rotate(200.0, angle_range=130.0)
        assert motor._lf.read() is None
        assert motor._rf.read() is None
