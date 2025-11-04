"""
Stepper motor control utilities shared across the application.
"""

from __future__ import annotations

import atexit
import logging
import time
from typing import Iterable, Tuple

try:
    import RPi.GPIO as GPIO  # type: ignore[import]

    _HAVE_GPIO = True
except ImportError:
    GPIO = None  # type: ignore[assignment]
    _HAVE_GPIO = False

LOGGER = logging.getLogger(__name__)

# BCM pin assignments
IN1, IN2, IN3, IN4 = 17, 18, 27, 22

# Half-step sequence definition
SEQ_FWD: Tuple[Tuple[int, int, int, int], ...] = (
    (1, 0, 0, 0),
    (1, 1, 0, 0),
    (0, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 0),
    (0, 0, 1, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
)

SEQ_REV: Tuple[Tuple[int, int, int, int], ...] = tuple(reversed(SEQ_FWD))

PINS = (IN1, IN2, IN3, IN4)


class StepperError(RuntimeError):
    """Raised when the stepper controller cannot satisfy a request."""


class StepperController:
    """
    Provides basic clockwise / counter-clockwise rotation for a four-wire
    stepper motor using half-step sequencing.
    """

    def __init__(self, *, enabled: bool | None = None, delay: float = 0.003) -> None:
        self.delay = delay
        self._enabled = bool(_HAVE_GPIO if enabled is None else enabled)

        if self._enabled:
            assert GPIO is not None  # for type-checkers
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PINS, GPIO.OUT, initial=GPIO.LOW)
        else:
            LOGGER.warning("RPi.GPIO not available; stepper controller running in dry-run mode")

    def spin(self, direction: str, steps: int, *, delay: float | None = None) -> None:
        if steps <= 0:
            raise StepperError("steps must be a positive integer")

        sequence = self._sequence_for(direction)
        self._run_sequence(sequence, steps, delay if delay is not None else self.delay)

    def cleanup(self) -> None:
        if not self._enabled:
            return

        assert GPIO is not None  # for type-checkers
        GPIO.output(PINS, GPIO.LOW)
        GPIO.cleanup()

    def _sequence_for(self, direction: str) -> Iterable[Tuple[int, int, int, int]]:
        if direction == "clockwise":
            # return SEQ_FWD
            return SEQ_REV

        if direction == "counter-clockwise":
            # return SEQ_REV
            return SEQ_FWD

        raise StepperError(f"unknown direction '{direction}'")

    def _run_sequence(
        self,
        sequence: Iterable[Tuple[int, int, int, int]],
        steps: int,
        delay: float,
    ) -> None:
        if not self._enabled:
            LOGGER.info("Stepper dry-run: %s steps with %.4fs delay", steps, delay)
            return

        assert GPIO is not None  # for type-checkers
        sequence = tuple(sequence)
        for idx in range(steps):
            a, b, c, d = sequence[idx % len(sequence)]
            GPIO.output(IN1, a)
            GPIO.output(IN2, b)
            GPIO.output(IN3, c)
            GPIO.output(IN4, d)
            time.sleep(delay)


controller = StepperController(delay=0.008)
atexit.register(controller.cleanup)

# Empirically calibrated step counts for this setup (roughly 180° / 360°).
PRESET_STEPS = {
    "half": 2137,
    "full": 4274,
}
