# RC-Car Projektdokumentation

## Projektübersicht

Ferngesteuertes Auto (ARRMA Granite GROM) mit Raspberry Pi 5 zur Steuerung über LTE/Internet via Webbrowser.

### Hardware

| Komponente | Modell |
|---|---|
| RC-Car | ARRMA Granite GROM (1:18) |
| Computer | Raspberry Pi 5 (8GB RAM) |
| Kamera | Raspberry Pi Camera Module 3 (IMX708) |
| LTE-Stick | Huawei Brovi E3372-325 |
| SIM-Karte | 1&1 (Telefónica/O2), 40 GB Datenvolumen, 50 Mbit/s |
| Servo-Controller | PCA9685 (16-Kanal PWM) |
| Stromversorgung | 2S LiPo 7.4V → REGU5A Step-Down (5V/5A) für Pi |
| Betriebssystem | Raspberry Pi OS Lite (Bookworm, 64-bit) |

### Software-Stack

| Komponente | Technologie |
|---|---|
| Kamera-Stream | Picamera2 + Hardware-MJPEG-Encoder + Flask |
| Steuerung | WebSocket (Flask-SocketIO) |
| Servo/Motor | PCA9685 via I²C (adafruit-circuitpython-pca9685) |
| LTE-Verbindung | usb_modeswitch + Huawei HiLink API |
| Frontend | HTML/CSS/JavaScript |

---

## Systemeinrichtung

### Raspberry Pi OS Lite installieren

1. Raspberry Pi Imager herunterladen
2. Raspberry Pi OS Lite (64-bit, Bookworm) auf SD-Karte flashen
3. Im Imager: WLAN, SSH und Benutzername konfigurieren

### Grundkonfiguration

```bash
sudo apt update && sudo apt upgrade -y
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → Camera → Enable
```

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

---

## Kamera-Stream (cam-stream.py)

```python
import io
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

camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (1200, 675)},
    controls={
        "FrameRate": 25,
        "AwbEnable": True,
        "AeEnable": True,
    },
    buffer_count=4
)
config["sensor"] = {"output_size": camera.sensor_resolution, "bit_depth": 10}
camera.configure(config)

output = StreamOutput()
camera.start_recording(MJPEGEncoder(bitrate=7500000), FileOutput(output))

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
    app.run(host='0.0.0.0', port=5000, threaded=True)
```

### Kamera-Stream als Service

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

### Alias für schnellen Start

```bash
echo 'alias startcam="cd ~/rc-car && source venv/bin/activate && python cam-stream.py"' >> ~/.bashrc
source ~/.bashrc
```

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
| 5 Mbit/s | niedrig | ~2.25 GB | ~17h |
| **7.5 Mbit/s** | **gut (aktuell)** | **~3.4 GB** | **~12h** |
| 8 Mbit/s | gut+ | ~3.6 GB | ~11h |
| 10 Mbit/s | sehr gut | ~4.5 GB | ~8-9h |

> **Bandbreite:** Der 1&1 Tarif mit 50 Mbit/s Download bietet typisch ~10-25 Mbit/s Upload über LTE. Der Stream benötigt 7.5 Mbit/s Upload → passt problemlos.

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
| `http://192.168.8.1` | Webinterface des Sticks |
| `sudo systemctl status lte-connect.service` | Auto-Connect Status |

---

## Stromversorgung

### Step-Down Modul (REGU5A)

| Parameter | Wert |
|---|---|
| Eingang | 4-38V (LiPo 2S: 7.4V) |
| Ausgang | 5V / max. 5A |
| Wirkungsgrad | ~85-90% |
| Abwärme | ~3-5W bei 3.5A Last |

#### Geschätzter Stromverbrauch

| Verbraucher | Stromaufnahme |
|---|---|
| Raspberry Pi 5 | ~2-3A |
| LTE-Stick (Brovi) | ~0.5A |
| PCA9685 + Servo | ~0.5A |
| Kamera | ~0.3A |
| **Gesamt** | **~3-4A** |

#### Montage-Hinweise

| Material | Erweichungstemperatur | Direkt montieren? |
|---|---|---|
| **PLA** (3D-Druck) | ~55-60°C | ❌ Verformt sich! |
| **ABS** (3D-Druck) | ~100°C | ✅ Safe |
| **PETG** (3D-Druck) | ~80°C | ⚠️ Knapp |
| **RC-Car Chassis** (Polycarbonat) | ~120-150°C | ✅ Kein Problem |

> **Empfehlung:** Alu-Kühlkörper mit Wärmeleitpad auf den REGU5A-Chip kleben + mit M3 Nylon-Abstandshaltern montieren.

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

---

## Nächste Schritte

- [x] LTE-Stick konfigurieren und testen ✅
- [x] Kamerastream optimieren (Hardware-MJPEG) ✅
- [ ] DuckDNS für feste Domain einrichten
- [ ] WebSocket-Steuerung (Lenkung + Gas) implementieren
- [ ] Frontend (HTML/JS) für Steuerung + Videostream
- [ ] PCA9685 Servo-Kalibrierung (Lenkung)
- [ ] ESC/Motor-Steuerung über PCA9685
- [ ] Latenz-Optimierung testen
- [ ] Sicherheits-Failsafe (Auto stoppt bei Verbindungsabbruch)
