# RC-Car Projekt Dokumentation
> Internet-/Webapp-gesteuertes RC-Car System mit Raspberry Pi 5

---

## Inhaltsverzeichnis
1. [Projektübersicht](#projektübersicht)
2. [Hardware Einkaufsliste](#hardware-einkaufsliste)
3. [Systemarchitektur](#systemarchitektur)
4. [Raspberry Pi Setup](#raspberry-pi-setup)
5. [Python Backend](#python-backend)
6. [Vue Frontend](#vue-frontend)
7. [Verkabelung](#verkabelung)
8. [Bekannte Probleme & Lösungen](#bekannte-probleme--lösungen)

---

## Projektübersicht

**Ziel:** Echtzeit-Steuerung eines RC-Cars über eine Webapp im Browser (inkl. PS4-Controller über Gamepad API), mit Live-Video-Stream.

**Technologie-Stack:**
- **Frontend:** Vue 3 + TypeScript + Pinia
- **Kommunikation:** WebSocket (Steuerung), MJPEG HTTP-Stream (Kamera)
- **Backend:** Python (asyncio + websockets + Flask)
- **Hardware:** Raspberry Pi 5, PCA9685 PWM-Treiber, Raspberry Pi Camera Module 3
- **Konnektivität:** LTE/4G (Huawei E3372h)
- **Fahrzeug:** ARRMA Granite Mega 665 1:10 4x4

---

## Hardware Einkaufsliste

### Fahrzeug
| Artikel | Preis |
|--------|-------|
| ARRMA Granite Mega 665 1:10 4x4 RTR (ohne Akku) | 168,00 € |

### Steuerrechner
| Artikel | Preis |
|--------|-------|
| Raspberry Pi 5, 4GB RAM | 116,50 € |
| Armor Gehäuse mit Lüfter (für Entwicklung) | 13,90 € |
| Raspberry Pi 27W USB-C Netzteil | 12,40 € |
| SanDisk Extreme 64GB A2 microSD | 24,90 € |

### Elektronik
| Artikel | Preis |
|--------|-------|
| PCA9685 16-Kanal PWM Servo Treiber (I2C) | 6,50 € |
| Raspberry Pi Camera Module 3, 12MP | 28,90 € |
| Step-Down Netzteilmodul 4-38V → 5V / 5A (REGU5A) | 4,80 € |

### Stromversorgung
| Artikel | Preis |
|--------|-------|
| GOLDBAT LiPo 2S 7,4V 6000mAh T-Plug (2 Pack) | 31,99 € |
| Haisito LiPo Ladegerät 80W 6A (inkl. Netzteil) | 39,94 € |
| Deans T-Plug Pigtail Kabel (offene Enden) | ~5,00 € |
| T-Plug Y-Splitter | ~3,00 € |

### Konnektivität & Controller
| Artikel | Preis |
|--------|-------|
| Huawei E3372h LTE-Stick | 41,95 € |
| PS4 DualShock 4 Controller | vorhanden |

### Kleinteile
| Artikel | Preis |
|--------|-------|
| ELEGOO Jumper Wire 40x20cm | 6,99 € |
| KUOQIY USB-C Kabel 5 Stück 30cm | 6,89 € |
| Tosiicop Deans T-Stecker Kabel | 8,40 € |
| Kabelbinder + Klettverschluss | ~5,00 € |

**Gesamtbudget: ca. 630 €**

---

## Systemarchitektur

```
PS4 Controller (Gamepad API)
        ↓
Browser Webapp (Vue 3)
        ↓ WebSocket Port 8765
Internet / LTE (Huawei E3372h)
        ↓
Raspberry Pi 5
    ↓               ↓
PCA9685          Flask MJPEG
(I2C)            Port 5000
    ↓               ↓
Servo + ESC     Camera Module 3
(Lenkung/Gas)   (IMX708 Sensor)
```

### Stromversorgung im Fahrzeug
```
LiPo 2S (7,4V)
      ↓
  Y-Splitter
  ↙        ↘
ESC        Step-Down (→ 5V)
(Motor)         ↓
           Raspberry Pi
           (versorgt PCA9685, LTE-Stick, Kamera)
```

---

## Raspberry Pi Setup

### Betriebssystem
**Raspberry Pi OS Lite 64-bit** — empfohlen statt Ubuntu Server da picamera2 und alle Pi-spezifischen Pakete direkt verfügbar sind.

> **Hinweis:** Ubuntu Server wurde initial verwendet, führte zu massiven Dependency-Problemen mit picamera2/libcamera. Wechsel zu Raspberry Pi OS Lite löste alle Probleme sofort.

### Headless Setup (Raspberry Pi Imager)
1. Raspberry Pi Imager öffnen
2. **Raspberry Pi OS Lite (64-bit)** auswählen
3. Zahnrad-Icon → Einstellungen:
   - Hostname: `rccar`
   - SSH aktivieren
   - WLAN SSID + Passwort
   - Benutzername + Passwort
4. SD-Karte flashen

### SSH Verbindung
```bash
ssh mikesraspberry@192.168.0.35
# oder
ssh mikesraspberry@rccar.local
```

### I2C aktivieren
```bash
sudo raspi-config
# → Interface Options → I2C → Enable
sudo reboot

# Testen ob PCA9685 erkannt wird
sudo i2cdetect -y 1
# Sollte 0x40 anzeigen
```

### Virtual Environment einrichten
```bash
cd ~/rc-car
python3 -m venv venv
source venv/bin/activate
```

### Pakete installieren
```bash
pip install websockets
pip install flask
pip install opencv-python
pip install adafruit-circuitpython-servokit
sudo apt install python3-picamera2 -y
```

### Aliases in ~/.bashrc
```bash
alias startcam='cd ~/rc-car && source venv/bin/activate && python3 cam-stream.py'
alias startrc='cd ~/rc-car && python3 ws-server.py'
alias startall='tmux new-session -d -s rc -n "main" && \
  tmux send-keys -t rc:main "cd ~/rc-car && source venv/bin/activate && python3 cam-stream.py" Enter && \
  tmux split-window -t rc:main -h && \
  tmux send-keys -t rc:main "cd ~/rc-car && source venv/bin/activate && python3 ws-server.py" Enter && \
  tmux attach -t rc'
```

---

## Python Backend

### cam-stream.py — MJPEG Kamera Stream

```python
import io
from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (854, 480)},  # 16:9 natives Seitenverhältnis
    controls={
        "FrameRate": 30,
        "AwbEnable": 1,  # Auto-Weißabgleich
    },
    buffer_count=2
)
# Maximalen Sensor-Bereich nutzen (IMX708: 4608x2592)
config["sensor"] = {"output_size": camera.sensor_resolution, "bit_depth": 10}
camera.configure(config)
camera.start()

def generate_frames():
    while True:
        frame = camera.capture_array()
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    response = Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

**Kamera-Optimierungen:**
- Auflösung 854x480 (echtes 16:9) für maximalen Sichtwinkel
- JPEG Qualität 50 für niedrige Latenz
- `buffer_count=2` für flüssigeren Stream
- Voller Sensor-Bereich genutzt (`sensor_resolution`)
- Auto-Weißabgleich aktiviert

### ws-server.py — WebSocket Steuerung + PCA9685

```python
import asyncio
import websockets
import json
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

# Kanäle
ESC_CHANNEL = 1      # Kanal 1 → ESC (Gas/Bremse) über EXT RX
SERVO_CHANNEL = 0    # Kanal 0 → Servo (Lenkung) direkt

# PWM Werte in Mikrosekunden
PWM_NEUTRAL   = 1500
PWM_FULL_FWD  = 2000
PWM_FULL_REV  = 1000
PWM_SERVO_MID = 1500
PWM_SERVO_MAX = 2000
PWM_SERVO_MIN = 1000

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
                usSteering = apply_steering(steering)
                usThrottle = apply_throttle(throttle)
                print(f"Throttle: {throttle:.2f} | Steering: {steering:.2f}")
                await ws.send(getDataJson(usThrottle, usSteering))
            except Exception as e:
                print("Error:", e)
    finally:
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
        set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
        set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)
        print("Server gestoppt.")
```

**PWM Werte Referenz:**
| Wert | µs | Bedeutung |
|------|----|-----------|
| throttle = 1.0 | 2000µs | Vollgas vorwärts |
| throttle = 0.5 | 1750µs | Halbgas vorwärts |
| throttle = 0.0 | 1500µs | Neutral |
| throttle = -0.5 | 1250µs | Halbe Bremse |
| throttle = -1.0 | 1000µs | Volle Bremse |
| steering = 1.0 | 2000µs | Voll rechts |
| steering = 0.0 | 1500µs | Geradeaus |
| steering = -1.0 | 1000µs | Voll links |

---

## Vue Frontend

### Projektstruktur
```
src/
├── components/
│   └── custom components/
│       └── CameraStream.vue
├── composables/
│   └── useGamepadWS.ts
├── stores/
│   └── rcControlStore.ts
└── views/
    └── RcControl.vue (Hauptview)
```

### useGamepadWS.ts — WebSocket Composable
```typescript
import { ref, onUnmounted } from 'vue'

export function useGamepadWS(url: string) {
    const ws = ref<WebSocket | null>(null)
    const connected = ref(false)
    const lastMessage = ref<any>(null)

    function connect() {
        ws.value = new WebSocket(url)
        ws.value.onopen = () => { connected.value = true }
        ws.value.onclose = () => {
            connected.value = false
            setTimeout(connect, 2000) // Auto-Reconnect
        }
        ws.value.onmessage = (event) => {
            try { lastMessage.value = JSON.parse(event.data) }
            catch (e) { console.error('Invalid WS response:', e) }
        }
        ws.value.onerror = (e) => console.error('WS Fehler:', e)
    }

    function sendControl(steering: number, throttle: number) {
        if (ws.value?.readyState === WebSocket.OPEN) {
            ws.value.send(JSON.stringify({
                steering: parseFloat(steering.toFixed(2)),
                throttle: parseFloat(throttle.toFixed(2))
            }))
        }
    }

    connect()
    onUnmounted(() => ws.value?.close())
    return { connected, sendControl, lastMessage }
}
```

### rcControlStore.ts — Pinia Store
```typescript
import { defineStore } from "pinia"
import { ref } from "vue"

export const useRcControl = defineStore("rcControl", {
    state: () => ({
        throttleIndex: 1,
        throttleGears: [33, 66, 99] as const,
        r1WasPressed: false,
        l1WasPressed: false,
        steeringOffset: ref(0.0),
        OFFSET_STEP: 0.01,
        OFFSET_MAX: 0.7,
    }),
    getters: {
        maxThrottle: (state): number => {
            return state.throttleGears[state.throttleIndex] ?? state.throttleGears[0]
        }
    },
    actions: {
        decreaseMaxThrottle() {
            if (this.throttleIndex > 0) this.throttleIndex--
        },
        increaseMaxThrottle() {
            if (this.throttleIndex < this.throttleGears.length - 1) this.throttleIndex++
        },
        handleButtonL1(gp: Gamepad) {
            const pressed = gp.buttons[13]?.pressed
            if (pressed && !this.l1WasPressed) this.decreaseMaxThrottle()
            this.l1WasPressed = pressed!
        },
        handleButtonR1(gp: Gamepad) {
            const pressed = gp.buttons[12]?.pressed
            if (pressed && !this.r1WasPressed) this.increaseMaxThrottle()
            this.r1WasPressed = pressed!
        },
        handleButtonLeft(gp: Gamepad) {
            if (gp.buttons[14]?.pressed) this.decreaseSteeringOffset()
        },
        handleButtonRight(gp: Gamepad) {
            if (gp.buttons[15]?.pressed) this.increaseSteeringOffset()
        },
        decreaseSteeringOffset() {
            this.steeringOffset = Math.max(-this.OFFSET_MAX,
                Math.round((this.steeringOffset - this.OFFSET_STEP) * 100) / 100)
        },
        increaseSteeringOffset() {
            this.steeringOffset = Math.min(this.OFFSET_MAX,
                Math.round((this.steeringOffset + this.OFFSET_STEP) * 100) / 100)
        },
        resetSteeringOffset() {
            this.steeringOffset = 0
        },
        applySteeringOffset(steering: number): number {
            // Steering ist invertiert + Offset anwenden
            return Math.max(-1, Math.min(1, (-steering) + (-this.steeringOffset)))
        },
    },
})
```

### PS4 Controller Mapping
| Button/Achse | Index | Funktion |
|-------------|-------|----------|
| Linker Stick X | axes[0] | Lenkung |
| R2 | buttons[7] | Gas vorwärts |
| L2 | buttons[6] | Bremse/Rückwärts |
| D-Pad Links | buttons[14] | Lenkung Offset - |
| D-Pad Rechts | buttons[15] | Lenkung Offset + |
| D-Pad Unten | buttons[13] | Gas-Modus runter (L1) |
| D-Pad Oben | buttons[12] | Gas-Modus hoch (R1) |

### CameraStream.vue
```vue
<template>
  <img 
    :src="`http://${piIp}:5000/video_feed`"
    style="width: 100%; height: auto;"
  />
</template>
```

---

## Verkabelung

### PCA9685 → Raspberry Pi (I2C)
| PCA9685 | Pi GPIO Pin |
|---------|-------------|
| VCC | Pin 2 (5V) |
| GND | Pin 6 (GND) |
| SDA | Pin 3 (GPIO2) |
| SCL | Pin 5 (GPIO3) |

### PCA9685 → ESC / Servo
| PCA9685 Kanal | Verbindung | Funktion |
|--------------|------------|----------|
| Kanal 0 | Servo direkt (aus STEER raus) | Lenkung |
| Kanal 1 | EXT RX am Spektrum ESC | Gas/Bremse |

### Stromversorgung
```
LiPo 7,4V → Y-Splitter
                ├── ESC (direkt, für Motor)
                └── Step-Down REGU5A (→ 5,1V)
                         └── Raspberry Pi (USB-C)
                                  └── PCA9685 (GPIO 5V)
                                  └── LTE-Stick (USB-A)
                                  └── Kamera (CSI)
```

### 3-Pin Servo/ESC Stecker Belegung
```
Pin 1 (oben)  = Signal (weiß/grau/gelb) → PWM am PCA9685
Pin 2 (mitte) = VCC (+)                 → V+ am PCA9685
Pin 3 (unten) = GND (-)                 → GND am PCA9685
```

---

## Bekannte Probleme & Lösungen

### Ubuntu Server → Raspberry Pi OS Wechsel
**Problem:** `python3-picamera2` und `libcamera` nicht in Ubuntu Noble Repos verfügbar. Stundenlange Dependency-Probleme.

**Lösung:** Wechsel zu **Raspberry Pi OS Lite 64-bit** — alle Pakete sofort verfügbar.

### I2C nicht aktiv
**Problem:** `ValueError: No Hardware I2C on (scl,sda)=(3, 2)`

**Lösung:**
```bash
sudo raspi-config → Interface Options → I2C → Enable
sudo reboot
```

### Lenkung invertiert
**Problem:** Links war rechts, rechts war links.

**Lösung:** Steering in `applySteeringOffset` negieren:
```typescript
return Math.max(-1, Math.min(1, (-steering) + (-this.steeringOffset)))
```

### Kalibrierungs-Offset invertiert
**Problem:** Nach Steering-Invertierung war auch der Offset falsch herum.

**Lösung:** Offset ebenfalls negieren (beide zusammen):
```typescript
(-steering) + (-this.steeringOffset)
```

### Spektrum ESC nicht per PWM ansteuerbar
**Problem:** Der originale Spektrum SLT2 2-in-1 ESC verwendet proprietäres SLT-Protokoll — kein Standard PWM.

**Lösung:** Hobbywing QuicRun 1060 Brushed ESC (~25€) als Ersatz — versteht Standard PWM direkt vom PCA9685.

### picamera2 pip vs apt Konflikt
**Problem:** pip-Version von picamera2 findet apt-installiertes libcamera nicht.

**Lösung:** pip-Version deinstallieren, apt-Version nutzen:
```bash
pip3 uninstall picamera2 -y --break-system-packages
sudo apt install python3-picamera2 -y
```

---

## Nächste Schritte

- [ ] Hobbywing QuicRun 1060 ESC kaufen und einbauen (~25€)
- [ ] Servo mechanisch kalibrieren (Spurstange anpassen)
- [ ] DuckDNS einrichten für feste Domain über LTE
- [ ] LTE-Stick konfigurieren und testen
- [ ] Alle Komponenten ins Chassis einbauen
- [ ] Erste Testfahrt

---

*Erstellt aus Chat-Verlauf — RC-Car Projekt mit Raspberry Pi 5*
