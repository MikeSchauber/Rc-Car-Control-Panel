import asyncio
import websockets
import json
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

# Kanäle
ESC_CHANNEL = 1      # Kanal 1 → ESC (Gas/Bremse)
SERVO_CHANNEL = 0    # Kanal 0 → Servo (Lenkung)

# PWM Werte in Mikrosekunden
PWM_NEUTRAL    = 1500
PWM_FULL_FWD   = 2000
PWM_FULL_REV   = 1000
PWM_SERVO_MID  = 1500
PWM_SERVO_MAX  = 2000
PWM_SERVO_MIN  = 1000

def set_pwm_us(channel: int, us: float):
    """Setzt PWM Wert in Mikrosekunden auf PCA9685"""
    # PCA9685 bei 50Hz: 20ms Periode = 20000µs
    # duty_cycle 0-65535
    pulse = int((us / 20000.0) * 65535)
    pulse = max(0, min(65535, pulse))
    kit.servo[channel]._pwm_out.duty_cycle = pulse

def apply_steering(value: float):
    """
    value: -1.0 (links) bis 1.0 (rechts)
    → 1000µs bis 2000µs
    """
    us = PWM_SERVO_MID + (value * 500)
    us = max(PWM_SERVO_MIN, min(PWM_SERVO_MAX, us))
    set_pwm_us(SERVO_CHANNEL, us)

def apply_throttle(value: float):
    """
    value > 0  → Vorwärts  (1500 - 2000µs)
    value = 0  → Neutral   (1500µs)
    value < 0  → Bremse    (1500 - 1000µs)

    Hinweis: Spektrum ESC braucht erst Bremse dann
    nochmal Bremse für Rückwärts (Double-Tap Reverse)
    """
    if value > 0:
        # Vorwärts
        us = PWM_NEUTRAL + (value * 500)
    elif value < 0:
        # Bremse / Rückwärts
        us = PWM_NEUTRAL + (value * 500)
    else:
        # Neutral
        us = PWM_NEUTRAL

    us = max(PWM_FULL_REV, min(PWM_FULL_FWD, us))
    set_pwm_us(ESC_CHANNEL, us)

# Beim Start alles auf Neutral
set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)

async def handler(ws):
    print("Client connected")
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                throttle = float(data.get("throttle", 0))
                steering = float(data.get("steering", 0))

                print(f"Throttle: {throttle:.2f} | Steering: {steering:.2f}")

                apply_steering(steering)
                apply_throttle(throttle)

                await ws.send(getDataJson(throttle, steering))

            except Exception as e:
                print("Error:", e)
    finally:
        # Sicherheit: wenn Client trennt → Neutral
        print("Client disconnected — Neutral")
        set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
        set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
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
        # Sicherheit: beim Beenden alles Neutral
        set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
        set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)
        print("Server gestoppt.")