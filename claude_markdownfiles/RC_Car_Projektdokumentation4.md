# RC-Car Projektdokumentation

## Projektübersicht

Ferngesteuertes Auto (ARRMA Granite GROM) mit Raspberry Pi 5 zur Steuerung über LTE/Internet via Webbrowser.

### Ziel

Ein RC-Car, das über das Internet von überall steuerbar ist – mit Live-Kamerabild und Controller-Unterstützung (PS4 Gamepad).

### Technologie-Stack

| Bereich | Technologie |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite |
| Backend | Python (Flask + WebSocket) |
| Hardware | Raspberry Pi 5, PCA9685, IMX708 Kamera |
| Kamera-Stream | Picamera2 + Hardware-MJPEG-Encoder + Flask |
| Verbindung | LTE (Huawei Brovi E3372-325) + Tailscale VPN |
| Steuerung | WebSocket (JSON) + Gamepad API |

---

## Hardware Einkaufsliste

### Fahrzeug

| Komponente | Modell | Preis |
|---|---|---|
| RC-Car | ARRMA Granite GROM (1:18) | ~130 € |
| LiPo-Akku | 2S 7.4V 1300mAh (im Set) | (enthalten) |
| USB-Ladegerät | (im Set enthalten) | (enthalten) |

### Steuerrechner

| Komponente | Modell | Preis |
|---|---|---|
| Raspberry Pi 5 | 8 GB RAM | ~95 € |
| MicroSD-Karte | SanDisk Extreme 64 GB | ~12 € |
| Kamera | Raspberry Pi Camera Module 3 (IMX708) | ~35 € |
| Kamera-Kabel | 22-pin → 15-pin FPC Adapter | ~5 € |

### Elektronik

| Komponente | Modell | Preis |
|---|---|---|
| Servo-Controller | PCA9685 (16-Kanal PWM) | ~5 € |
| Ersatz-Servo | SG90 / MG90S (falls nötig) | ~5 € |
| Jumper-Kabel | 40 Stk. Female-Female | ~3 € |

### Stromversorgung

| Komponente | Modell | Preis |
|---|---|---|
| Step-Down Modul | REGU5A (4-38V → 5V / 5A) | ~12 € |
| USB-C Kabel | kurz, gewinkelt, für Pi-Stromversorgung | ~5 € |
| Kondensator (Eingang) | 2200µF 16V Low-ESR Elko | ~1 € |
| Kondensator (Ausgang) | 470µF 6.3V Low-ESR Elko | ~0.50 € |
| Schottky-Diode | SS34 (3A, 40V) | ~0.30 € |

### Konnektivität

| Komponente | Modell | Preis |
|---|---|---|
| LTE-Stick | Huawei Brovi E3372-325 | ~40 € |
| SIM-Karte | 1&1 (O2), 40 GB, 50 Mbit/s | ~10 €/M |

### Kleinteile

| Komponente | Modell | Preis |
|---|---|---|
| Abstandshalter | M3 Nylon Spacer Set | ~5 € |
| Schrauben | M2.5 / M3 Set | ~5 € |
| Kabelbinder | div. Größen | ~3 € |
| Doppelseitiges Klebeband | 3M VHB | ~5 € |
| Schrumpfschlauch | div. Größen | ~3 € |

### Gesamtbudget: ca. 380 € (einmalig) + ~10 €/Monat SIM

---

## Systemarchitektur

### Systemübersicht

```
                    ┌──────────────────────────────┐
                    │      Vue 3 Frontend           │
                    │   (Browser / Handy / Laptop)  │
                    │                               │
                    │   Gamepad API → WebSocket     │
                    │   <img> → MJPEG Stream        │
                    └───────────┬───────────────────┘
                                │ Tailscale VPN / LTE
                    ┌───────────▼───────────────────┐
                    │      Raspberry Pi 5            │
                    │                               │
                    │  cam-stream.py (Flask :5000)   │
                    │  ws-server.py  (WS :8765)      │
                    │                               │
                    │  I²C → PCA9685                 │
                    └──┬─────────┬─────────┬────────┘
                       │         │         │
                    Servo     ESC       Kamera
                  (Lenkung)  (Motor)   (IMX708)
```

### Stromversorgung

```
LiPo 2S 7.4V
    │
    ├──[Schottky-Diode]──[2200µF Elko]──→ REGU5A ──[470µF Elko]──→ 5V
    │                                                    │
    │                                          ┌─────────┼──────────┐
    │                                          │         │          │
    │                                     Pi (USB-C)  PCA9685 V+  LTE-Stick
    │                                          │
    │                                     PCA9685 VCC (nur Logik, 3.3V)
    │
    └──→ ESC (Motor direkt vom LiPo)
```

> **Wichtig:** PCA9685 V+ (Servo-Power) muss **separat** vom Step-Down versorgt werden, **nicht** über den Pi's GPIO 5V Pin. Sonst zieht der ESC den Pi-Strom runter → USB-Geräte sterben.

---

## Raspberry Pi Setup

### Betriebssystem

- Raspberry Pi OS Lite (Bookworm, 64-bit)
- Headless Setup (kein Monitor)

### Grundkonfiguration

```bash
sudo apt update && sudo apt upgrade -y
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → Camera → Enable
```

### SSH (Headless)

```bash
# Auf dem PC verbinden
ssh mikesraspberry@192.168.0.36
```

### USB Stromlimit aufheben

Da der Pi mit Step-Down statt offiziellem USB-PD Netzteil betrieben wird, begrenzt er USB auf 600mA. Fix:

```bash
sudo nano /boot/firmware/config.txt
```

Am Ende einfügen:

```
usb_max_current_enable=1
```

Hebt das Limit auf **1.6A** an → LTE-Stick bekommt genug Strom.

### Python Virtual Environment

```bash
python3 -m venv --system-site-packages ~/rc-car/venv
source ~/rc-car/venv/bin/activate
```

### Pakete installieren

```bash
pip install flask flask-socketio adafruit-circuitpython-pca9685
```

> **Hinweis:** `opencv-python` wird seit dem Umstieg auf den Hardware-MJPEG-Encoder nicht mehr für den Kamera-Stream benötigt. Optional installieren falls für andere Zwecke (z.B. Bildverarbeitung) gewünscht:
> ```bash
> pip install opencv-python  # optional
> ```

### Aliases

```bash
echo 'alias startcam="cd ~/rc-car && source venv/bin/activate && python cam-stream.py"' >> ~/.bashrc
echo 'alias startcam-indoor="cd ~/rc-car && source venv/bin/activate && BITRATE=7500000 RES=1200x675 FPS=25 python cam-stream.py"' >> ~/.bashrc
echo 'alias startcam-outdoor="cd ~/rc-car && source venv/bin/activate && BITRATE=3000000 RES=854x480 FPS=15 python cam-stream.py"' >> ~/.bashrc
echo 'alias ltecheck="ping -c 2 -I usb0 8.8.8.8 && curl -s --interface usb0 ifconfig.me && echo \"\""' >> ~/.bashrc
source ~/.bashrc
```

---

## Python Backend

### cam-stream.py (Kamera-Stream)

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

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# Konfigurierbar über Umgebungsvariablen (für Indoor/Outdoor Profile)
bitrate = int(os.environ.get("BITRATE", 7500000))
res = os.environ.get("RES", "1200x675").split("x")
fps = int(os.environ.get("FPS", 25))

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
            output.condition.wait()
            frame = output.frame
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
    print(f"Kamera: {res[0]}x{res[1]} @ {fps}fps, {bitrate/1000000:.1f} Mbit/s")
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

### cam-stream.service

```bash
sudo nano /etc/systemd/system/cam-stream.service
```

```ini
[Unit]
Description=RC-Car Kamera Stream
After=network.target

[Service]
Type=simple
User=mikesraspberry
WorkingDirectory=/home/mikesraspberry/rc-car
ExecStart=/home/mikesraspberry/rc-car/venv/bin/python cam-stream.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cam-stream.service
sudo systemctl start cam-stream.service
```

### ws-server.py (WebSocket-Steuerung mit Watchdog-Failsafe)

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

WATCHDOG_TIMEOUT = 0.5  # 500ms ohne Signal → Neutral

last_message_time = 0

def set_pwm_us(channel, us):
    pulse = int((us / 20000.0) * 65535)
    pulse = max(0, min(65535, pulse))
    kit.servo[channel]._pwm_out.duty_cycle = pulse

def apply_steering(value):
    us = PWM_SERVO_MID + (value * 500)
    us = max(PWM_SERVO_MIN, min(PWM_SERVO_MAX, us))
    set_pwm_us(SERVO_CHANNEL, us)
    return us

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
    set_pwm_us(ESC_CHANNEL, PWM_NEUTRAL)
    set_pwm_us(SERVO_CHANNEL, PWM_SERVO_MID)
    print("⚠️ FAILSAFE → Neutral!")

# Watchdog: prüft ob noch Signale kommen
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
        print(f"Watchdog aktiv: {WATCHDOG_TIMEOUT}s Timeout")
        asyncio.create_task(watchdog())
        await asyncio.Future()

if __name__ == "__main__":
    go_neutral()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        go_neutral()
        print("Server gestoppt.")
```

### PWM Werte Referenz

| Funktion | PWM (µs) | Wert |
|---|---|---|
| ESC Neutral | 1500 | Motor aus |
| ESC Vollgas vorwärts | 2000 | Max vorwärts |
| ESC Vollgas rückwärts | 1000 | Max rückwärts |
| Servo Mitte | 1500 | Geradeaus |
| Servo Max Links | 1000 | Vollanschlag links |
| Servo Max Rechts | 2000 | Vollanschlag rechts |

### Watchdog-Failsafe

| Situation | Reaktion |
|---|---|
| Browser geschlossen | `finally` → sofort Neutral ✅ |
| LTE bricht ab (stille Trennung) | Watchdog → nach 500ms Neutral ✅ |
| WebSocket hängt | Watchdog → nach 500ms Neutral ✅ |
| Normales Fahren | `last_message_time` wird aktualisiert → kein Eingriff |

> **Wichtig:** Das Frontend muss auch bei Stillstand regelmäßig (~100ms) Daten senden, damit der Watchdog nicht auslöst.

---

## Kamera-Optimierungen

### Hardware-MJPEG Encoder (statt OpenCV)

Die alte Version nutzte `cv2.imencode()` → CPU-basiertes JPEG-Encoding. Die neue Version nutzt den **Hardware-MJPEG-Encoder** des Raspberry Pi 5 (über ISP/PiSP).

| | Alt (OpenCV) | Neu (Hardware MJPEG) |
|---|---|---|
| **Encoding** | CPU (cv2) | Hardware (PiSP) |
| **Auflösung** | 640x360 | 1200x675 |
| **FPS** | 30 | 25 |
| **Bitrate** | ~3-5 Mbit/s (variabel) | 7.5 Mbit/s (steuerbar) |
| **CPU-Last** | ~40-60% | ~5-10% |
| **Latenz** | ~150-300ms | ~80-150ms |

> **Hinweis:** Der Raspberry Pi 5 hat **keinen Hardware-H.264/HEVC-Encoder**. Broadcom hat den Encoder im VideoCore VII entfernt – nur noch Hardware-**Decoder** für H.264/H.265 sind vorhanden. Hardware-MJPEG über den ISP ist daher die effizienteste Option.

### Picamera2 Farb-Controls

| Control | Bereich | Was es macht |
|---|---|---|
| `Brightness` | -1.0 bis 1.0 | Gesamthelligkeit |
| `Contrast` | 0.0 bis 2.0 | Unterschied hell/dunkel |
| `Saturation` | 0.0 bis 2.0 | Farbintensität |
| `ColourGains` | (R, B) je 0.0-8.0 | Rot/Blau-Anteil manuell (Grün = Referenz) |
| `AwbMode` | 0-6 | Weißabgleich-Preset (0=Auto, 5=Daylight) |
| `ExposureValue` | -8.0 bis 8.0 | Belichtungskorrektur |

> **Hinweis `ColourGains`:** Es gibt nur Rot- und Blau-Gain. Grün ist die Referenz (immer 1.0). Für mehr Grün → Rot und Blau runterdrehen, z.B. `(0.7, 0.7)`.

### Datenverbrauch über LTE

| Bitrate | Qualität | Pro Stunde | 40 GB Fahrzeit |
|---|---|---|---|
| 3 Mbit/s | niedrig (Outdoor) | ~1.35 GB | ~29h |
| 5 Mbit/s | mittel | ~2.25 GB | ~17h |
| **7.5 Mbit/s** | **gut (Indoor, aktuell)** | **~3.4 GB** | **~12h** |
| 8 Mbit/s | gut+ | ~3.6 GB | ~11h |
| 10 Mbit/s | sehr gut | ~4.5 GB | ~8-9h |

> **Bandbreite:** Der 1&1 Tarif mit 50 Mbit/s Download bietet typisch ~10-25 Mbit/s Upload über LTE. Der Stream benötigt 7.5 Mbit/s Upload → passt problemlos.

### Indoor/Outdoor Profile

| Profil | Auflösung | FPS | Bitrate | Alias |
|---|---|---|---|---|
| **Indoor** | 1200x675 | 25 | 7.5 Mbit | `startcam-indoor` |
| **Outdoor** | 854x480 | 15 | 3 Mbit | `startcam-outdoor` |

---

## LTE-Stick Einrichtung (Huawei Brovi E3372-325)

### Stick-Erkennung & usb_modeswitch

Der Brovi E3372-325 (Vendor ID `3566:2001`) wird zunächst als CD-ROM-Gerät erkannt und muss per `usb_modeswitch` in den Netzwerk-Modus (HiLink) umgeschaltet werden.

#### Voraussetzungen installieren
```bash
sudo apt update && sudo apt install -y usb-modeswitch usb-modeswitch-data
```

#### udev-Regel anlegen
```bash
sudo nano /etc/udev/rules.d/40-huawei.rules
```

Inhalt:
```
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

Nach dem Einstecken wechselt die Device ID von `3566:2001` → `12d1:155e` und ein `usb0` Interface erscheint.

#### Prüfen ob Stick erkannt wird
```bash
lsusb
# Sollte "12d1:155e Huawei Technologies Co., Ltd. Mobile" zeigen

ip link show
# Sollte "usb0" Interface anzeigen

ip addr show usb0
# Sollte IP im Bereich 192.168.8.x zeigen
```

### SIM-PIN per API entsperren

Die Huawei API benötigt für jeden Request einen CSRF-Token.

```bash
# Token + Cookie holen
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

# PIN senden
curl -X POST http://192.168.8.1/api/pin/operate \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><OperateType>0</OperateType><CurrentPin>DEINE_PIN</CurrentPin></request>'
```

**SIM-Status prüfen:**
```bash
curl -s http://192.168.8.1/api/pin/status
```

| SimState | Bedeutung |
|----------|-----------|
| 257 | SIM entsperrt ✅ |
| 260 | SIM PIN-gesperrt 🔒 |

> **Hinweis:** PIN-Deaktivierung (`OperateType: 1`) funktioniert bei der Brovi-Firmware nicht über die API (Error `101005`). Alternative: PIN am Windows-PC über `http://192.168.8.1` deaktivieren.

### Datenverbindung aufbauen

```bash
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

curl -X POST http://192.168.8.1/api/dialup/dial \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
```

| Action | Bedeutung |
|--------|-----------|
| 1 | Verbinden |
| 0 | Trennen |

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

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| ConnectMode | 0 | Auto-Connect |
| AutoReconnect | 1 | Bei Abbruch neu verbinden |
| MaxIdelTime | 0 | Kein Timeout |

### Automatischer Start nach Reboot (Systemd)

Da die PIN nicht deaktiviert werden konnte, übernimmt ein Startup-Script automatisch PIN-Eingabe und Einwahl.

#### Script anlegen
```bash
sudo nano /usr/local/bin/lte-connect.sh
```

```bash
#!/bin/bash
sleep 20

# Warten bis Stick bereit
for i in {1..30}; do
  curl -s http://192.168.8.1/api/webserver/SesTokInfo > /dev/null 2>&1 && break
  sleep 2
done

# Token holen
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

# PIN senden
curl -X POST http://192.168.8.1/api/pin/operate \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><OperateType>0</OperateType><CurrentPin>3200</CurrentPin></request>'

sleep 5

# Neuer Token für Dial
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')

# Verbinden
curl -X POST http://192.168.8.1/api/dialup/dial \
  -H "Content-Type: application/xml" \
  -H "__RequestVerificationToken: $TOKEN" \
  -b "SessionID=$COOKIE" \
  -d '<?xml version="1.0" encoding="UTF-8"?><request><Action>1</Action></request>'
```

```bash
sudo chmod +x /usr/local/bin/lte-connect.sh
```

#### Systemd Service anlegen
```bash
sudo nano /etc/systemd/system/lte-connect.service
```

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

```bash
sudo systemctl enable lte-connect.service
```

### LED-Status (Brovi E3372-325)

> **Hinweis:** Die Brovi-Variante zeigt im USB-Tethering/HiLink-Modus ein **rotes Dauerlicht** — das ist **kein Fehler**, sondern normales Verhalten. Die LED-Farben unterscheiden sich vom klassischen Huawei E3372h.

### Quick-Check Befehle

| Befehl | Was es zeigt |
|--------|-------------|
| `lsusb` | Stick erkannt? (`12d1:155e`) |
| `ip link show` | `usb0` Interface vorhanden? |
| `ip addr show usb0` | IP `192.168.8.x` zugewiesen? |
| `ping -c 4 8.8.8.8` | Internet erreichbar? |
| `ping -c 4 -I usb0 8.8.8.8` | Internet über LTE (auch wenn WLAN an)? |
| `curl -s --interface usb0 ifconfig.me` | Öffentliche IP über LTE? |
| `http://192.168.8.1` | Webinterface des Sticks |
| `sudo systemctl status lte-connect.service` | Auto-Connect Status |

---

## Netzwerk & Fernzugriff

### Problem: LTE-Stick von außen nicht erreichbar

Der Huawei E3372h im HiLink-Modus ist ein eigenständiger Mini-Router mit NAT-Firewall:

- ❌ Kein Port-Forwarding konfigurierbar
- ❌ Kein DMZ / UPnP
- ❌ 1&1/O2 gibt meistens nur IPv6 (mit CGNAT auf IPv4)

```
Internet → [CGNAT O2] → [LTE-Stick NAT/Firewall] → Pi
              ❌                    ❌
```

Von außen direkt auf den Pi zugreifen: **nicht möglich**.

### Lösung: Tailscale VPN

Tailscale baut einen verschlüsselten Tunnel **von innen nach außen** auf → funktioniert durch jede Firewall/NAT.

#### Installation auf dem Pi

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
sudo tailscale up
```

Beim ersten `tailscale up` kommt ein Login-Link → im Browser öffnen und bestätigen.

#### Tailscale IP abfragen

```bash
tailscale ip -4       # z.B. 100.85.46.43
tailscale status      # Zeigt alle Geräte + Verbindungstyp
```

#### Auf PC/Handy

Tailscale installieren (https://tailscale.com/download), gleicher Account. Fertig.

#### In der Vue App

```typescript
const WS_URL = 'ws://100.85.46.43:8765'            // Steuerung
const CAM_URL = 'http://100.85.46.43:5000/video_feed'  // Kamera
```

#### Verbindungstyp prüfen

| Anzeige in `tailscale status` | Bedeutung | Latenz |
|---|---|---|
| `direct 192.x.x.x:41641` | Peer-to-Peer ✅ | Schnell (~20-50ms) |
| `relay "fra"` | Über DERP-Server ❌ | Langsam (~100-300ms) |

> **Notiz:** Verbindung mit Tailscale funktioniert, ist aber teilweise langsam über Relay. Evtl. eigenen VPN-Server einrichten (OpenVPN auf TP-Link AX3000 oder WireGuard).

### LTE als Fallback-Route (wenn WLAN ausfällt)

Ohne Konfiguration verliert der Pi Internet wenn WLAN weg ist, obwohl LTE aktiv ist. Fix:

```bash
sudo nano /etc/dhcpcd.conf
```

Am Ende einfügen:

```
interface usb0
static routers=192.168.8.1
static domain_name_servers=8.8.8.8 8.8.4.4
metric 200

interface wlan0
metric 100
```

```bash
sudo systemctl restart dhcpcd
```

| Situation | Default Route | Tailscale |
|---|---|---|
| **WLAN an** | `wlan0` (metric 100, bevorzugt) | ✅ läuft über WLAN |
| **WLAN aus** | `usb0` LTE (metric 200, Fallback) | ✅ läuft über LTE |
| **Beides an** | WLAN bevorzugt, LTE Fallback | ✅ |

#### Fallback Route Script (zusätzliche Absicherung)

```bash
sudo nano /usr/local/bin/setup-routes.sh
```

```bash
#!/bin/bash

# Warten bis usb0 da ist
for i in {1..30}; do
  ip link show usb0 up > /dev/null 2>&1 && break
  sleep 2
done

# LTE als Fallback-Route
ip route add default via 192.168.8.1 dev usb0 metric 200 2>/dev/null

echo "Routen gesetzt:"
ip route show default
```

```bash
sudo chmod +x /usr/local/bin/setup-routes.sh
```

```bash
sudo nano /etc/systemd/system/setup-routes.service
```

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

```bash
sudo systemctl enable setup-routes.service
```

---

## Stromversorgung

### Step-Down Modul (REGU5A)

| Parameter | Wert |
|---|---|
| Eingang | 4-38V (LiPo 2S: 7.4V) |
| Ausgang | 5V / max. 5A |
| Wirkungsgrad | ~85-90% |
| Abwärme | ~3-5W bei 3.5A Last |

### Geschätzter Stromverbrauch

| Verbraucher | Stromaufnahme |
|---|---|
| Raspberry Pi 5 | ~2-3A |
| LTE-Stick (Brovi) | ~0.5A |
| PCA9685 + Servo | ~0.5A |
| Kamera | ~0.3A |
| **Gesamt** | **~3-4A** |

### Brownout-Schutz (Kondensatoren)

Beim Gas geben zieht der Motor **20-30A Spikes** → Batteriespannung sackt ab → Pi brownout. Fix:

| Komponente | Position | Preis |
|---|---|---|
| **2200µF 16V Low-ESR Elko** | Eingang REGU5A (parallel) | ~1 € |
| **470µF 6.3V Low-ESR Elko** | Ausgang REGU5A (parallel) | ~0.50 € |
| **SS34 Schottky-Diode** | Zwischen Y-Splitter und Step-Down | ~0.30 € |

```
LiPo → Y-Splitter ──→ ESC (Motor direkt)
                   └─[Schottky-Diode]→ [2200µF Elko] → REGU5A → [470µF Elko] → 5V → Pi
```

### PCA9685 V+ separat versorgen

**Problem:** ESC zieht über PCA9685 Strom vom Pi's 5V-Rail → USB-Geräte (LTE-Stick) sterben.

**Lösung:** V+ Jumper auf PCA9685 auftrennen, V+ direkt vom Step-Down versorgen:

```
Step-Down 5V ──→ Pi (USB-C)           ← Pi, Kamera, LTE-Stick
             └──→ PCA9685 V+ (Klemme) ← Servo + ESC Signal-Strom

Pi GPIO Pin 2 ──→ PCA9685 VCC         ← nur Logik (paar mA)
Pi GPIO Pin 6 ──→ PCA9685 GND
Pi GPIO Pin 3 ──→ PCA9685 SDA
Pi GPIO Pin 5 ──→ PCA9685 SCL
```

### Montage-Hinweise (Hitze)

| Material | Erweichungstemperatur | Direkt montieren? |
|---|---|---|
| **PLA** (3D-Druck) | ~55-60°C | ❌ Verformt sich! |
| **ABS** (3D-Druck) | ~100°C | ✅ Safe |
| **PETG** (3D-Druck) | ~80°C | ⚠️ Knapp |
| **RC-Car Chassis** (Polycarbonat) | ~120-150°C | ✅ Kein Problem |

> **Empfehlung:** Alu-Kühlkörper mit Wärmeleitpad auf den REGU5A-Chip kleben + mit M3 Nylon-Abstandshaltern montieren.

### Einkauf Elektronik-Bauteile

| Shop | Lieferzeit | Anmerkung |
|---|---|---|
| **reichelt.de** | 1-2 Tage | Günstig, super Auswahl |
| **pollin.de** | 1-2 Tage | Günstige Bauteile |
| **conrad.de** | 1-2 Tage | Alles, aber teurer |
| **Amazon** | 1 Tag (Prime) | Wenn's schnell gehen muss |
| **mükra electronic (Göppingen)** | Vor Ort | ~80 km von Scheer |

---

## Verkabelung

### Übersicht

| Von | Nach | Kabel |
|---|---|---|
| LiPo 2S 7.4V | Y-Splitter | XT30-Stecker |
| Y-Splitter | ESC | XT30 |
| Y-Splitter | Schottky-Diode → REGU5A Eingang | Kabel + Elko |
| REGU5A Ausgang | Pi (USB-C) | USB-C Kabel |
| REGU5A Ausgang | PCA9685 V+ (Schraubklemme) | Kabel direkt |
| Pi GPIO | PCA9685 (VCC, GND, SDA, SCL) | Jumper-Kabel |
| PCA9685 Kanal 0 | Servo (Lenkung) | Servo-Kabel |
| PCA9685 Kanal 1 | ESC (Signal) | Servo-Kabel |
| Pi USB | LTE-Stick | direkt einstecken |
| Pi CSI | Kamera (IMX708) | FPC-Kabel |

### PCA9685 Pin-Belegung

| PCA9685 | Raspberry Pi 5 |
|---|---|
| VCC | Pin 2 (5V) – nur Logik! |
| GND | Pin 6 (GND) |
| SDA | Pin 3 (GPIO 2) |
| SCL | Pin 5 (GPIO 3) |
| V+ | **Direkt vom REGU5A 5V** (nicht über Pi!) |

> **Wichtig:** V+ Jumper auf dem PCA9685 Board **auftrennen**! Sonst wird der Servo-Strom über den Pi gezogen.

---

## Bekannte Probleme & Lösungen

### RGB/BGR Farbproblem (Picamera2 + OpenCV)

**Problem:** Picamera2 gibt Frames als **RGB** aus, OpenCV (`cv2.imencode`) erwartet **BGR**. Ohne Konvertierung sind Rot und Blau vertauscht.

**Fix (bei Verwendung von OpenCV):**
```python
frame = camera.capture_array()
frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
ret, buffer = cv2.imencode('.jpg', frame)
```

> Durch den Wechsel auf den **Hardware-MJPEG-Encoder** ist `cv2` nicht mehr nötig – das Problem tritt nicht mehr auf.

### Spektrum ESC nicht per PWM steuerbar

**Problem:** Der originale ARRMA/Spektrum ESC reagiert nicht auf PWM-Signale vom PCA9685.

**Lösung:** Günstigen Standard-ESC verwenden (z.B. Hobbywing QuicRun) der normales PWM akzeptiert.

### LTE-Stick Error 125002 (Token fehlt)

**Problem:** API-Calls an den Huawei-Stick geben Error `125002` zurück.

**Lösung:** Jeder API-Request braucht einen frischen CSRF-Token:
```bash
TOKEN=$(curl -s http://192.168.8.1/api/webserver/SesTokInfo | grep -oP '(?<=<TokInfo>).*(?=</TokInfo>)')
COOKIE=$(curl -s -c - http://192.168.8.1/api/webserver/SesTokInfo | grep SessionID | awk '{print $NF}')
```

### LTE-Stick Error 101005 (PIN deaktivieren)

**Problem:** PIN-Deaktivierung über API gibt Error `101005` bei Brovi-Firmware.

**Lösung:** Startup-Script (`lte-connect.sh`) sendet PIN automatisch bei jedem Boot.

### Pi Brownout beim Gas geben

**Problem:** Motor-Spikes (20-30A) lassen die Batteriespannung einbrechen → Pi stürzt ab.

**Lösung:**
1. Kondensatoren auf Step-Down (2200µF Eingang + 470µF Ausgang)
2. Schottky-Diode zwischen Y-Splitter und Step-Down
3. PCA9685 V+ separat versorgen

### LTE-Stick LED aus nach ESC einschalten

**Problem:** ESC zieht über PCA9685 Strom vom Pi's 5V-Rail → USB Strom reicht nicht für LTE-Stick.

**Lösung:**
1. `usb_max_current_enable=1` in `/boot/firmware/config.txt`
2. PCA9685 V+ **separat** vom Step-Down versorgen (V+ Jumper auftrennen)

### Kein Internet über LTE nach WLAN-Ausfall

**Problem:** Pi hat keine Default-Route über `usb0` wenn WLAN ausfällt.

**Lösung:** `dhcpcd.conf` mit Metriken konfigurieren (wlan0: 100, usb0: 200) + Fallback-Route Script.

---

## Nächste Schritte

- [x] LTE-Stick konfigurieren und testen ✅
- [x] Kamerastream optimieren (Hardware-MJPEG) ✅
- [x] Tailscale Fernzugriff einrichten ✅
- [x] WebSocket Failsafe/Watchdog ✅
- [ ] Eigenen VPN-Server einrichten (OpenVPN/WireGuard) — *Notiz: Tailscale funktioniert, aber Verbindung teilweise langsam über Relay. Evtl. eigener VPN-Server performanter.*
- [ ] DuckDNS für feste Domain einrichten
- [ ] Kondensatoren einlöten (2200µF + 470µF + Schottky-Diode)
- [ ] PCA9685 V+ separat versorgen (Jumper auftrennen)
- [ ] Servo mechanisch kalibrieren
- [ ] Alle Komponenten ins Chassis einbauen
- [ ] Erste Testfahrt 🚗
