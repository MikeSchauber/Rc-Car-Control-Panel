import asyncio
import websockets
import json
import time
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

ESC_CHANNEL = 1
SERVO_CHANNEL = 0

PWM_NEUTRAL   = 1500
PWM_FULL_FWD  = 2000
PWM_FULL_REV  = 1000
PWM_SERVO_MID = 1500
PWM_SERVO_MAX = 2000
PWM_SERVO_MIN = 1000

WATCHDOG_TIMEOUT = 0.5

last_message_time = 0
current_steering_us = PWM_SERVO_MID
MAX_STEP = 30  # Max µs Änderung pro Update → sanfte Bewegung

def set_pwm_us(channel, us):
    pulse = int((us / 20000.0) * 65535)
    pulse = max(0, min(65535, pulse))
    kit.servo[channel]._pwm_out.duty_cycle = pulse

def apply_steering(value):
    global current_steering_us
    target_us = PWM_SERVO_MID + (value * 500)
    target_us = max(PWM_SERVO_MIN, min(PWM_SERVO_MAX, target_us))

    # Sanft zum Ziel bewegen (max MAX_STEP µs pro Update)
    diff = target_us - current_steering_us
    if abs(diff) > MAX_STEP:
        current_steering_us += MAX_STEP if diff > 0 else -MAX_STEP
    else:
        current_steering_us = target_us

    set_pwm_us(SERVO_CHANNEL, current_steering_us)
    return current_steering_us

def apply_throttle(value):
    if value > 0:
        us = PWM_NEUTRAL + (value * 500)
    elif value < 0:
        us = PWM_NEUTRAL + (value * 500)
    else:
        us = PWM_NEUTRAL
    us = max(PWM_FULL_REV, min(PWM_FULL_FWD, us))
    set_pwm_us(ESC_CHANNEL, us)
    return us

def go_neutral():
    global current_steering_us
    set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
    set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)
    current_steering_us = PWM_SERVO_MID
    print("⚠️ FAILSAFE → Neutral!")

async def watchdog():
    global last_message_time
    while True:
        await asyncio.sleep(0.1)
        if last_message_time > 0 and (time.time() - last_message_time) > WATCHDOG_TIMEOUT:
            go_neutral()
            last_message_time = 0

async def handler(ws):
    global last_message_time
    print("Client connected")
    last_message_time = time.time()
    try:
        async for msg in ws:
            try:
                last_message_time = time.time()
                data = json.loads(msg)
                throttle = float(data.get("throttle", 0))
                steering = float(data.get("steering", 0))
                usSteering = apply_steering(steering)
                usThrottle = apply_throttle(throttle)
                await ws.send(json.dumps({
                    "status": "ok",
                    "received_throttle": usThrottle,
                    "received_steering": usSteering
                }))
            except Exception as e:
                print("Error:", e)
    finally:
        print("Client disconnected → Neutral")
        go_neutral()
        last_message_time = 0

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket running on port 8765")
        print(f"Watchdog: {WATCHDOG_TIMEOUT}s | Servo-Ramping: {MAX_STEP}µs/step")
        asyncio.create_task(watchdog())
        await asyncio.Future()

if __name__ == "__main__":
    go_neutral()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        go_neutral()
        print("Server gestoppt.")