
# RC-Car Projekt Dokumentation

Internet-/Webapp-gesteuertes RC-Car System mit Raspberry Pi 5

## Inhaltsverzeichnis
- [Projektübersicht](#projektübersicht)
- [Hardware Einkaufsliste](#hardware-einkaufsliste)
- [Systemarchitektur](#systemarchitektur)
- [Raspberry Pi Setup](#raspberry-pi-setup)
- [Python Backend](#python-backend)
- [Vue Frontend](#vue-frontend)
- [Kamera-Optimierungen](#kamera-optimierungen)
- [LTE-Stick Einrichtung (Huawei Brovi E3372-325)](#lte-stick-einrichtung-huawei-brovi-e3372-325)
- [Netzwerk & Fernzugriff](#netzwerk--fernzugriff)
- [Stromversorgung](#stromversorgung)
- [Verkabelung](#verkabelung)
- [Bekannte Probleme & Lösungen](#bekannte-probleme--lösungen)
- [Nächste Schritte](#nächste-schritte)

## Projektübersicht

**Ziel:** Echtzeit-Steuerung eines RC-Cars über eine Webapp im Browser (inkl. PS4-Controller über Gamepad API), mit Live-Video-Stream.

**Technologie-Stack:**
- **Frontend:** Vue 3 + TypeScript + Pinia
- **Kommunikation:** WebSocket (Steuerung), MJPEG HTTP-Stream (Kamera)
- **Backend:** Python (asyncio + websockets + Flask)
- **Hardware:** Raspberry Pi 5, PCA9685 PWM-Treiber, Raspberry Pi Camera Module 3
- **Konnektivität:** LTE/4G (Huawei / Brovi E3372-325)
- **Fahrzeug:** ARRMA Granite Mega 665 1:10 4x4

## Hardware Einkaufsliste

### Fahrzeug

| Artikel | Preis |
|---|---:|
| ARRMA Granite Mega 665 1:10 4x4 RTR (ohne Akku) | 168,00 € |

### Steuerrechner

| Artikel | Preis |
|---|---:|
| Raspberry Pi 5, 4GB RAM | 116,50 € |
| Armor Gehäuse mit Lüfter (für Entwicklung) | 13,90 € |
| Raspberry Pi 27W USB-C Netzteil | 12,40 € |
| SanDisk Extreme 64GB A2 microSD | 24,90 € |

### Elektronik

| Artikel | Preis |
|---|---:|
| PCA9685 16-Kanal PWM Servo Treiber (I2C) | 6,50 € |
| Raspberry Pi Camera Module 3, 12MP | 28,90 € |
| Step-Down Netzteilmodul 4-38V → 5V / 5A (REGU5A) | 4,80 € |
| 2200µF 16V Low-ESR Elko | ~1,00 € |
| 470µF 6,3V Low-ESR Elko | ~0,50 € |
| SS34 / SS54 Schottky-Diode | ~0,30 € |

### Stromversorgung

| Artikel | Preis |
|---|---:|
| GOLDBAT LiPo 2S 7,4V 6000mAh (2 Pack) | 31,99 € |
| Haisito LiPo Ladegerät 80W 6A | 39,94 € |
| Deans T-Plug Pigtail Kabel | ~5,00 € |
| T-Plug Y-Splitter | ~3,00 € |

### Konnektivität & Controller

| Artikel | Preis |
|---|---:|
| Huawei / Brovi E3372-325 LTE-Stick | 41,95 € |
| PS4 DualShock 4 Controller | vorhanden |

### Kleinteile

| Artikel | Preis |
|---|---:|
| ELEGOO Jumper Wire 40x20cm | 6,99 € |
| USB-C Kabel 30cm | 6,89 € |
| Deans T-Stecker Kabel | 8,40 € |
| Kabelbinder + Klettverschluss | ~5,00 € |

**Gesamtbudget: ca. 630 €**

## Systemarchitektur

```text
PS4 Controller (Gamepad API)
        ↓
Browser Webapp (Vue 3)
        ↓ WebSocket Port 8765
Internet / LTE (Huawei / Brovi E3372-325)
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

```text
LiPo 2S (7,4V)
      ↓
  Y-Splitter
  ↙        ↘
ESC        Step-Down (→ 5V)
(Motor)         ↓
           Raspberry Pi
           (versorgt LTE-Stick, Kamera, I2C-Logik)

WICHTIG:
Servo-/ESC-Leistungsversorgung möglichst nicht über den Pi führen.
PCA9685 V+ separat versorgen bzw. Hardware entlasten.
```

## Raspberry Pi Setup

### Betriebssystem

**Raspberry Pi OS Lite 64-bit** — empfohlen statt Ubuntu Server, da picamera2 und Pi-spezifische Pakete direkt verfügbar sind.

### Headless Setup (Raspberry Pi Imager)
- Raspberry Pi OS Lite (64-bit)
- SSH aktivieren
- WLAN SSID + Passwort
- Benutzername + Passwort
- Hostname setzen

### SSH Verbindung
```bash
ssh mikesraspberry@192.168.0.36
```

### I2C aktivieren
```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
sudo i2cdetect -y 1
```

### Virtual Environment
```bash
cd ~/rc-car
python3 -m venv venv
source venv/bin/activate
```

### Pakete installieren
```bash
pip install websockets flask adafruit-circuitpython-servokit
sudo apt install python3-picamera2 -y
```

**Optional:**
```bash
pip install opencv-python
```
Nur falls OpenCV für andere Experimente gebraucht wird. Für den aktuellen Stream nicht mehr nötig.

### USB Stromlimit aufheben
```bash
sudo nano /boot/firmware/config.txt
```
Am Ende einfügen:
```ini
usb_max_current_enable=1
```
Danach:
```bash
sudo reboot
```

### Aliases in `~/.bashrc`
```bash
alias startcam='cd ~/rc-car && source venv/bin/activate && python3 cam-stream.py'
alias startrc='cd ~/rc-car && source venv/bin/activate && python3 ws-server.py'
alias startcam-indoor='cd ~/rc-car && source venv/bin/activate && BITRATE=7500000 RES=1200x675 FPS=25 python3 cam-stream.py'
alias startcam-outdoor='cd ~/rc-car && source venv/bin/activate && BITRATE=3000000 RES=854x480 FPS=15 python3 cam-stream.py'
alias ltecheck='ping -c 2 -I usb0 8.8.8.8 && curl -s --interface usb0 ifconfig.me && echo ""'
```

## Python Backend

### `cam-stream.py` — Hardware MJPEG mit Frame-Drop gegen Buffer-Stau
```python
import io
import os
from flask import Flask, Response
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import threading

app = Flask(__name__)

class StreamOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()
        self.new_frame = False

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.new_frame = True
            self.condition.notify_all()

bitrate = int(os.environ.get("BITRATE", 5000000))
res = os.environ.get("RES", "854x480").split("x")
fps = int(os.environ.get("FPS", 30))

camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (int(res[0]), int(res[1]))},
    controls={
        "FrameRate": fps,
        "AwbEnable": True,
        "AeEnable": True,
    },
    buffer_count=4
)
config["sensor"] = {"output_size": camera.sensor_resolution, "bit_depth": 10}
camera.configure(config)

output = StreamOutput()
camera.start_recording(MJPEGEncoder(bitrate=bitrate), FileOutput(output))

def generate_frames():
    while True:
        with output.condition:
            output.condition.wait(timeout=0.1)
            if not output.new_frame or output.frame is None:
                continue
            frame = output.frame
            output.new_frame = False
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
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

### `ws-server.py` — WebSocket Steuerung + Watchdog + Servo-Ramping
```python
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
MAX_STEP = 30

last_message_time = 0
current_steering_us = PWM_SERVO_MID

def set_pwm_us(channel, us):
    pulse = int((us / 20000.0) * 65535)
    pulse = max(0, min(65535, pulse))
    kit.servo[channel]._pwm_out.duty_cycle = pulse

def apply_steering(value):
    global current_steering_us
    target_us = PWM_SERVO_MID + (value * 500)
    target_us = max(PWM_SERVO_MIN, min(PWM_SERVO_MAX, target_us))

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
    print("FAILSAFE -> Neutral")

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
                us_steering = apply_steering(steering)
                us_throttle = apply_throttle(throttle)
                await ws.send(json.dumps({
                    "status": "ok",
                    "received_throttle": us_throttle,
                    "received_steering": us_steering
                }))
            except Exception as e:
                print("Error:", e)
    finally:
        print("Client disconnected -> Neutral")
        go_neutral()
        last_message_time = 0

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        asyncio.create_task(watchdog())
        await asyncio.Future()

if __name__ == "__main__":
    go_neutral()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        go_neutral()
        print("Server gestoppt")
```

### PWM Werte Referenz

| Wert | µs | Bedeutung |
|---|---:|---|
| throttle = 1.0 | 2000 | Vollgas vorwärts |
| throttle = 0.5 | 1750 | Halbgas vorwärts |
| throttle = 0.0 | 1500 | Neutral |
| throttle = -0.5 | 1250 | Halbe Bremse |
| throttle = -1.0 | 1000 | Volle Bremse |
| steering = 1.0 | 2000 | Voll rechts |
| steering = 0.0 | 1500 | Geradeaus |
| steering = -1.0 | 1000 | Voll links |

## Vue Frontend

### Projektstruktur
```text
src/
├── components/
│   └── CameraStream.vue
├── composables/
│   └── useGamepadWS.ts
├── stores/
│   └── rcControlStore.ts
└── views/
    └── RcControl.vue
```

### `useGamepadWS.ts`
```ts
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
            setTimeout(connect, 2000)
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

### `rcControlStore.ts`
```ts
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
            return Math.max(-1, Math.min(1, (-steering) + (-this.steeringOffset)))
        },
    },
})
```

### PS4 Controller Mapping

| Button/Achse | Index | Funktion |
|---|---:|---|
| Linker Stick X | axes[0] | Lenkung |
| R2 | buttons[7] | Gas vorwärts |
| L2 | buttons[6] | Bremse/Rückwärts |
| D-Pad Links | buttons[14] | Lenkung Offset - |
| D-Pad Rechts | buttons[15] | Lenkung Offset + |
| D-Pad Unten | buttons[13] | Gas-Modus runter |
| D-Pad Oben | buttons[12] | Gas-Modus hoch |

### `CameraStream.vue`
```vue
<template>
  <img :src="`http://${piIp}:5000/video_feed`" style="width: 100%; height: auto;" />
</template>
```

## Kamera-Optimierungen

### Alt vs Neu

| Thema | Alte Version | Neue Version |
|---|---|---|
| Encoding | OpenCV JPEG per CPU | Hardware MJPEG |
| Typische Auflösung | 640x360 | 854x480 / 1200x675 |
| CPU-Last | deutlich höher | deutlich niedriger |
| Lag über LTE | konnte sich aufstauen | besser wegen Frame-Drop |
| Farbe | RGB/BGR-Probleme möglich | kein OpenCV-Farbproblem mehr |

### Pi 5 Encoder-Hinweis
Der Raspberry Pi 5 hat **keinen Hardware-H.264/HEVC-Encoder** mehr. Für dieses Projekt ist Hardware-MJPEG über Picamera2/PiSP der pragmatischste Weg.

### Picamera2 Farb-Controls

| Control | Bereich | Wirkung |
|---|---|---|
| Brightness | -1.0 bis 1.0 | Gesamthelligkeit |
| Contrast | 0.0 bis 2.0 | Kontrast |
| Saturation | 0.0 bis 2.0 | Farbsättigung |
| ColourGains | (R, B) | Rot-/Blau-Anteil |
| AwbMode | 0-6 | Weißabgleich-Preset |
| ExposureValue | -8 bis 8 | Belichtungskorrektur |

**Hinweis:** Grün gibt es bei `ColourGains` nicht separat. Grün ist die Referenz, steuerbar nur indirekt über Rot/Blau.

### Datenverbrauch über LTE

| Bitrate | Pro Stunde | 40 GB reichen für |
|---|---:|---:|
| 5 Mbit/s | ~2,25 GB | ~17-18 h |
| 7,5 Mbit/s | ~3,4 GB | ~11-12 h |
| 8 Mbit/s | ~3,6 GB | ~11 h |
| 10 Mbit/s | ~4,5 GB | ~8-9 h |

### 1&1 / LTE Hinweis
Ein 50-Mbit-Tarif reicht grundsätzlich, entscheidend ist aber der **Upload**. Für 7,5 Mbit Stream muss der reale Upload stabil genug sein.

## LTE-Stick Einrichtung (Huawei Brovi E3372-325)

### Erkennung
Typischer Ausgangszustand:
- `3566:2001` → CD-ROM / Umschaltmodus
- nach Umschalten z. B. `12d1:155e`

### Pakete
```bash
sudo apt update
sudo apt install -y usb-modeswitch usb-modeswitch-data
```

### udev-Regel
Datei:
```bash
sudo nano /etc/udev/rules.d/40-huawei.rules
```
Inhalt:
```text
ACTION!="add", GOTO="modeswitch_rules_end"
SUBSYSTEM!="usb", GOTO="modeswitch_rules_end"

ATTRS{bInterfaceNumber}!="00", GOTO="modeswitch_rules_end"

ATTRS{bDeviceClass}=="e0", GOTO="modeswitch_rules_begin"
ATTRS{bInterfaceClass}=="e0", GOTO="modeswitch_rules_begin"
GOTO="modeswitch_rules_end"

LABEL="modeswitch_rules_begin"
ATTRS{idVendor}=="3566", ATTRS{idProduct}=="2001", RUN+="/sbin/usb_modeswitch -v 3566 -p 2001 -W -R -w 400"
ATTRS{idVendor}=="3566", ATTRS{idProduct}=="2001", RUN+="/sbin/usb_modeswitch -v 3566 -p 2001 -W -R"

LABEL="modeswitch_rules_end"
```

### SIM PIN entsperren
Jeder Request braucht frischen Token/Cookie:
```bash
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/pin/operate \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><OperateType>0</OperateType><CurrentPin>3200</CurrentPin></request>'
```

### Datenverbindung verbinden
```bash
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/dialup/dial \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
```

### Auto-Connect aktivieren
```bash
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/dialup/connection \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><RoamAutoConnectEnable>0</RoamAutoConnectEnable><AutoReconnect>1</AutoReconnect><MaxIdelTime>0</MaxIdelTime><ConnectMode>0</ConnectMode></request>'
```

### `/usr/local/bin/lte-connect.sh`
```bash
#!/bin/bash
sleep 20

for i in {1..30}; do
  curl -s http://192.168.8.1/api/webserver/SesTokInfo > /dev/null 2>&1 && break
  sleep 2
done

TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/pin/operate \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><OperateType>0</OperateType><CurrentPin>3200</CurrentPin></request>'

sleep 5

TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/dialup/dial \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
```

### Systemd Service
Datei `/etc/systemd/system/lte-connect.service`:
```ini
[Unit]
Description=LTE Stick Auto-Connect
After=network.target
Wants=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lte-connect.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```
Aktivieren:
```bash
sudo chmod +x /usr/local/bin/lte-connect.sh
sudo systemctl enable lte-connect.service
```

### LED Status
Bei der Brovi-Variante ist **rotes Dauerlicht** nicht automatisch ein Fehler. Wenn Internet geht, ist die LED-Farbe alleine nicht aussagekräftig.

### Quick-Check

| Befehl | Zweck |
|---|---|
| `lsusb` | Stick erkannt? |
| `ip -br addr show` | `usb0` vorhanden? |
| `ip addr show usb0` | 192.168.8.x vorhanden? |
| `ping -c 4 -I usb0 8.8.8.8` | Internet über LTE? |
| `curl -s --interface usb0 ifconfig.me` | WAN-IP über LTE |

## Netzwerk & Fernzugriff

### NAT / Firewall Problem
Der LTE-Stick arbeitet als Router/NAT. Eingehende Ports auf Pi-Diensten sind dadurch problematisch bzw. blockiert.

### Tailscale
Installieren:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
sudo tailscale up
```
Eigene Tailscale-IP anzeigen:
```bash
tailscale ip -4
```
Status:
```bash
tailscale status
```

### Tailscale Verbindungsarten
- `direct` = gut
- `relay` = funktioniert, aber langsamer

**Notiz:** Verbindung mit Tailscale schlecht aber möglich. Evtl. eigenen VPN-Server erstellen.

### LTE Fallback-Route
`wlan0` bevorzugen, `usb0` als Fallback:

`/etc/dhcpcd.conf` ergänzen:
```ini
interface usb0
static routers=192.168.8.1
static domain_name_servers=8.8.8.8 8.8.4.4
metric 200

interface wlan0
metric 100
```

### `setup-routes.sh`
```bash
#!/bin/bash
for i in {1..30}; do
  ip link show usb0 > /dev/null 2>&1 && break
  sleep 2
done
ip route add default via 192.168.8.1 dev usb0 metric 200 2>/dev/null
ip route show default
```

### Service für Fallback-Route
`/etc/systemd/system/setup-routes.service`:
```ini
[Unit]
Description=Setup LTE Fallback Route
After=network-online.target lte-connect.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-routes.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

## Stromversorgung

### REGU5A
- Eingang: 4–38V
- Ausgang: 5V / bis 5A
- typischer Wirkungsgrad: ca. 85–90%
- dadurch mehrere Watt Verlustwärme möglich

### Abschätzung Stromaufnahme

| Verbraucher | ca. Strom |
|---|---:|
| Raspberry Pi 5 | 2–3 A |
| LTE-Stick aktiv | 0,3–0,8 A |
| Kamera | ~0,3 A |
| PCA9685 + Servo-Spikes | 0,5–1,5 A |
| Gesamt unter Last | kritisch nahe am Limit |

### Montage / Wärme

| Material | Bewertung |
|---|---|
| PLA | kritisch, kann weich werden |
| PETG | grenzwertig |
| ABS | besser |
| robustes Chassis-Material | meist ok |

**Empfehlung:** kleine Alu-Fläche / Kühlkörper + Abstandshalter verwenden.

### Brownout-Fix mit Kondensatoren
Empfohlen:
- 2200µF 16V Low-ESR am Eingang des Step-Down
- 470µF 6,3V Low-ESR am Ausgang des Step-Down
- optional SS34 / SS54 Schottky-Diode

### Aktueller Praxis-Fix
Da getrennte Versorgung für PCA9685 V+ aktuell schwer umzusetzen ist, wurde das Problem softwareseitig stark entschärft durch:
- Servo-Ramping (`MAX_STEP = 30`)
- reduzierte Stromspitzen beim Lenken

## Verkabelung

### PCA9685 → Raspberry Pi (I2C)

| PCA9685 | Pi GPIO Pin |
|---|---|
| VCC | 5V (nur Logik) |
| GND | GND |
| SDA | GPIO2 / Pin 3 |
| SCL | GPIO3 / Pin 5 |

### PCA9685 → ESC / Servo

| Kanal | Verbindung | Funktion |
|---|---|---|
| Kanal 0 | Servo direkt | Lenkung |
| Kanal 1 | Hobbywing QuicRun 1060 | Gas / Bremse |

### Wichtiger Hinweis zu V+
Die Leistungsversorgung `V+` des PCA9685 sollte idealerweise **nicht dauerhaft über den Pi** geführt werden, wenn LTE-Stick und Servo gleichzeitig Last ziehen. In der aktuellen Zwischenlösung bleibt alles verbunden, aber Servo-Ramping reduziert die Spitzen.

## Bekannte Probleme & Lösungen

### Ubuntu Server → Raspberry Pi OS Wechsel
**Problem:** picamera2 / libcamera auf Ubuntu problematisch.
**Lösung:** Raspberry Pi OS Lite 64-bit.

### I2C nicht aktiv
**Problem:** `No Hardware I2C`.
**Lösung:** I2C in `raspi-config` aktivieren.

### Lenkung invertiert
**Problem:** links/rechts vertauscht.
**Lösung:** Steering im Frontend negieren.

### Kalibrierungs-Offset invertiert
**Problem:** Offset nach Invertierung falsch herum.
**Lösung:** Offset ebenfalls negieren.

### Spektrum ESC nicht per PWM ansteuerbar
**Problem:** Originaler Spektrum ESC versteht kein Standard-PWM.
**Lösung:** Hobbywing QuicRun 1060 verwenden.

### picamera2 pip vs apt Konflikt
**Problem:** pip-Version von picamera2 kollidiert mit apt-libcamera.
**Lösung:** apt-Version nutzen.

### RGB/BGR Farbproblem
**Problem:** Farben wirkten vertauscht, Blau/Rot falsch.
**Ursache:** Picamera2 liefert RGB, OpenCV erwartet BGR.
**Lösung:** `cv2.cvtColor(..., cv2.COLOR_RGB2BGR)` oder besser direkt Hardware-MJPEG ohne OpenCV nutzen.

### LTE API Error 125002
**Problem:** Request auf API liefert 125002.
**Ursache:** fehlender Request-Token.
**Lösung:** vor API-Requests frischen Token/Cookie holen.

### LTE API Error 101005
**Problem:** PIN deaktivieren per API schlug fehl.
**Lösung:** auf Brovi-Firmware teils nicht unterstützt; stattdessen PIN beim Boot senden.

### LTE-Stick nicht erkannt / kein `usb0`
**Problem:** Stick erscheint nicht oder bleibt dunkel.
**Lösung:** `usb_max_current_enable=1`, `usb_modeswitch`, Stromversorgung prüfen.

### Pi Brownout beim Lenken
**Problem:** Pi stürzt bei schnellen Lenkbewegungen unter LTE-Last ab.
**Ursache:** Servo-Spike + LTE-Stick-Sendeleistung ziehen gemeinsam zu viel Strom.
**Lösung:** Servo-Ramping (`MAX_STEP=30`) als wirksamer Software-Fix; langfristig Kondensatoren / sauberere Stromtrennung.

### Stream-Lag wird mit der Zeit schlimmer
**Problem:** je länger der Stream läuft, desto größer der Verzögerungsstau.
**Lösung:** altes MJPEG-Skript so angepasst, dass immer nur neue Frames verarbeitet werden (`new_frame` Flag + Timeout).

### Tailscale draußen langsamer
**Problem:** außerhalb des WLAN teils schlechtere Verbindung.
**Ursache:** LTE-Funklöcher oder Tailscale Relay.
**Lösung:** Outdoor-Profil nutzen, Tailscale-Status prüfen, ggf. eigener VPN-Server.

## Nächste Schritte

- [x] LTE-Stick konfigurieren und testen
- [x] Kamerastream auf Hardware-MJPEG umstellen
- [x] WebSocket Failsafe / Watchdog einbauen
- [x] Servo-Ramping gegen Brownout-Spikes einbauen
- [x] Erste erfolgreiche Testfahrt über LTE außerhalb des WLAN-Bereichs
- [x] Tailscale Fernzugriff einrichten
- [ ] Eigenen VPN-Server einrichten (OpenVPN / WireGuard)
- [ ] DuckDNS für feste Domain einrichten
- [ ] Kondensatoren einlöten (2200µF + 470µF + Schottky)
- [ ] Stromversorgung langfristig robuster machen
- [ ] Servo mechanisch kalibrieren
- [ ] Alle Komponenten final ins Chassis einbauen
- [ ] Weitere Testfahrten / Funkloch-Karte erstellen

### Fazit Stand 03.06.2026
- Erste erfolgreiche Fahrt über LTE außerhalb des WLAN-Bereichs geschafft.
- Servo-Ramping (`MAX_STEP=30`) behebt das Brownout-Problem aktuell ausreichend gut per Software.
- Verbindung ist grundsätzlich stabil genug zum Fahren, hat aber in bestimmten Bereichen noch Einbrüche — vermutlich LTE-Signal / Tailscale Relay.

_Erstellt und fortlaufend aktualisiert aus Chat-Verlauf — RC-Car Projekt mit Raspberry Pi 5_
