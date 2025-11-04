"""
Servo motor control utilities to manage the rudder angle.
"""

from __future__ import annotations

import atexit
import logging
from typing import Optional

try:
    import RPi.GPIO as GPIO  # type: ignore[import]

    _HAVE_GPIO = True
except ImportError:
    GPIO = None  # type: ignore[assignment]
    _HAVE_GPIO = False

LOGGER = logging.getLogger(__name__)

SERVO_PIN = 23
PWM_FREQUENCY = 50  # Hz

MIN_ANGLE = -80.0
MAX_ANGLE = 80.0

MIN_DUTY = 5.0   # ~1 ms pulse at 50 Hz
MAX_DUTY = 10.0  # ~2 ms pulse at 50 Hz


class ServoError(RuntimeError):
    """Raised when the servo controller cannot satisfy a request."""


class ServoController:
    """
    Basic servo controller that converts desired angles to duty cycles on a PWM pin.
    Uses a safe dry-run mode when RPi.GPIO is unavailable.
    """

    def __init__(
        self,
        *,
        pin: int = SERVO_PIN,
        frequency: int = PWM_FREQUENCY,
        enabled: Optional[bool] = None,
        min_angle: float = MIN_ANGLE,
        max_angle: float = MAX_ANGLE,
        min_duty: float = MIN_DUTY,
        max_duty: float = MAX_DUTY,
    ) -> None:
        self.pin = pin
        self.frequency = frequency
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_duty = min_duty
        self.max_duty = max_duty
        self._enabled = bool(_HAVE_GPIO if enabled is None else enabled)
        self._pwm = None
        self._angle = 0.0

        if self._enabled:
            assert GPIO is not None  # for type-checkers
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, self.frequency)
            self._pwm.start(self._duty_for_angle(self._angle))
        else:
            LOGGER.warning("RPi.GPIO not available; servo controller running in dry-run mode")

    @property
    def angle(self) -> float:
        return self._angle

    def set_angle(self, angle: float) -> float:
        clamped = max(self.min_angle, min(self.max_angle, angle))
        duty_cycle = self._duty_for_angle(clamped)

        if self._enabled:
            assert self._pwm is not None
            self._pwm.ChangeDutyCycle(duty_cycle)
        else:
            LOGGER.info("Servo dry-run: angle %.2f -> duty %.2f", clamped, duty_cycle)

        self._angle = clamped
        return clamped

    def cleanup(self) -> None:
        if not self._enabled:
            return

        assert GPIO is not None
        assert self._pwm is not None
        self._pwm.stop()
        GPIO.cleanup(self.pin)

    def _duty_for_angle(self, angle: float) -> float:
        span = self.max_angle - self.min_angle
        if span <= 0:
            raise ServoError("invalid servo configuration: max_angle must exceed min_angle")

        normalized = (angle - self.min_angle) / span
        return self.min_duty + normalized * (self.max_duty - self.min_duty)


controller = ServoController()
atexit.register(controller.cleanup)

