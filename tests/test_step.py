import RPi.GPIO as GPIO
import time

IN1, IN2, IN3, IN4 = 17, 18, 27, 22  # BCM numbering

# Half-step sequence (adjust to your motor if needed)
SEQ_FWD = [
    (1,0,0,0),
    (1,1,0,0),
    (0,1,0,0),
    (0,1,1,0),
    (0,0,1,0),
    (0,0,1,1),
    (0,0,0,1),
    (1,0,0,1),
]
SEQ_REV = SEQ_FWD[::-1]  # reverse copy, doesn't mutate the original

PINS = [IN1, IN2, IN3, IN4]

GPIO.setmode(GPIO.BCM)
GPIO.setup(PINS, GPIO.OUT, initial=GPIO.LOW)

def step(seq, steps, delay=0.003):
    n = len(seq)
    for i in range(steps):
        a,b,c,d = seq[i % n]
        GPIO.output(IN1, a)
        GPIO.output(IN2, b)
        GPIO.output(IN3, c)
        GPIO.output(IN4, d)
        time.sleep(delay)

try:
    # Try forward 512 steps
    step(SEQ_FWD, 512, delay=0.003)
    time.sleep(0.5)
    # Then reverse 512 steps
    step(SEQ_REV, 512, delay=0.003)

finally:
    # De-energize coils
    GPIO.output(PINS, GPIO.LOW)
    GPIO.cleanup()
