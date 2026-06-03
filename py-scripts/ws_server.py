import asyncio
import websockets
import json
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

ESC_CHANNEL = 1
SERVO_CHANNEL = 0

PWM_NEUTRAL    = 1500
PWM_FULL_FWD   = 2000
PWM_FULL_REV   = 1000
PWM_SERVO_MID  = 1500
PWM_SERVO_MAX  = 2000
PWM_SERVO_MIN  = 1000

WATCHDOG_TIMEOUT = 0.5  # Sekunden ohne Signal → Neutral

def set_pwm_us(channel: int, us: float):
    pulse = int((us / 20000.0) * 65535)
    pulse = max(0, min(65535, pulse))
    kit.servo[channel]._pwm_out.duty_cycle = pulse

def apply_steering(value: float):
    us = PWM_SERVO_MID + (value * 500)
    us = max(PWM_SERVO_MIN, min(PWM_SERVO_MAX, us))
    set_pwm_us(SERVO_CHANNEL, us)
    return us

def apply_throttle(value: float):
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
    set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
    set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)

go_neutral()

async def watchdog(last_msg_time, ws):
    while not ws.closed:
        await asyncio.sleep(0.1)
        if (asyncio.get_event_loop().time() - last_msg_time[0]) > WATCHDOG_TIMEOUT:
            go_neutral()
    go_neutral()

async def handler(ws):
    print("Client connected")
    last_msg_time = [asyncio.get_event_loop().time()]
    watchdog_task = asyncio.create_task(watchdog(last_msg_time, ws))

    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                throttle = float(data.get("throttle", 0))
                steering = float(data.get("steering", 0))

                last_msg_time[0] = asyncio.get_event_loop().time()

                usSteering = apply_steering(steering)
                usThrottle = apply_throttle(throttle)

                print(f"Throttle: {throttle:.2f} | Steering: {steering:.2f}")
                await ws.send(getDataJson(usThrottle, usSteering))

            except Exception as e:
                print("Error:", e)
    finally:
        watchdog_task.cancel()
        go_neutral()
        print("Client disconnected — Neutral")

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765, ping_interval=1, ping_timeout=3):
        print("WebSocket running on port 8765")
        await asyncio.Future()

def getDataJson(throttle, steering):
    return json.dumps({
        "status": "ok",
        "received_throttle": throttle,
        "received_steering": steering
    })

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        go_neutral()
        print("Server gestoppt.")