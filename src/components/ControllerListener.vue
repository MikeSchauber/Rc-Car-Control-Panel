<script lang="ts" setup>
import { useGamepadWS } from '@/composeables/useGamepadWS'
import { onMounted, onUnmounted, ref } from 'vue'

const logs = ref<string[]>([])
const gamepadIndex = ref<number | null>(null)
let animationFrameId: number | null = null

const { connected, sendControl } = useGamepadWS('ws://DEINE_PI_IP:8765')

function log(msg: string) {
    const time = new Date().toLocaleTimeString('de-DE', { hour12: false })
    logs.value.unshift(`[${time}] ${msg}`)
    if (logs.value.length > 50) logs.value.pop()
}

function pollGamepad() {
    if (gamepadIndex.value === null) return

    const gp = navigator.getGamepads()[gamepadIndex.value]
    if (!gp) return

    // Steuerung an Pi senden
    const steering = gp.axes[0]   // Linker Stick X
    const throttle = gp.buttons[6]  // R2

    if (steering && throttle) {
        sendControl(steering, throttle.value)
    }

    // Achsen loggen wenn Bewegung
    gp.axes.forEach((val, i) => {
        if (Math.abs(val) > 0.1) {
            log(`Achse ${i}: ${val.toFixed(3)}`)
        }
    })

    // Buttons loggen wenn gedrückt
    gp.buttons.forEach((btn, i) => {
        if (btn.pressed) {
            log(`Button ${i} gedrückt (value: ${btn.value.toFixed(2)})`)
        }
    })

    animationFrameId = requestAnimationFrame(pollGamepad)
}

onMounted(() => {
    window.addEventListener('gamepadconnected', (e) => {
        gamepadIndex.value = e.gamepad.index
        log(`✅ Controller verbunden: "${e.gamepad.id}"`)
        log(`   Achsen: ${e.gamepad.axes.length} | Buttons: ${e.gamepad.buttons.length}`)
        animationFrameId = requestAnimationFrame(pollGamepad)
    })

    window.addEventListener('gamepaddisconnected', (e) => {
        log(`❌ Controller getrennt: "${e.gamepad.id}"`)
        gamepadIndex.value = null
        if (animationFrameId) cancelAnimationFrame(animationFrameId)
    })
})

onUnmounted(() => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId)
})
</script>

<template>
    <div class="container">
        <h1>Gamepad Logger</h1>

        <div class="status-row">
            <p v-if="gamepadIndex === null" class="hint">
                Controller verbinden und eine Taste drücken...
            </p>
            <p v-else class="connected">Controller aktiv (Index {{ gamepadIndex }})</p>

            <p :class="connected ? 'ws-connected' : 'ws-disconnected'">
                WebSocket: {{ connected ? '🟢 verbunden' : '🔴 getrennt' }}
            </p>
        </div>

        <div class="log-box">
            <div v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</div>
            <div v-if="logs.length === 0" class="empty">Keine Eingaben...</div>
        </div>
    </div>
</template>

<style scoped>
.container {
    font-family: monospace;
    padding: 2rem;
    max-width: 700px;
}

.status-row {
    display: flex;
    gap: 2rem;
    align-items: center;
}

.hint {
    color: #888;
}

.connected {
    color: #22c55e;
    font-weight: bold;
}

.ws-connected {
    color: #22c55e;
    font-weight: bold;
}

.ws-disconnected {
    color: #ef4444;
    font-weight: bold;
}

.log-box {
    margin-top: 1rem;
    background: #111;
    color: #0f0;
    padding: 1rem;
    border-radius: 8px;
    height: 400px;
    overflow-y: auto;
    font-size: 13px;
}

.log-line {
    padding: 2px 0;
    border-bottom: 1px solid #1a1a1a;
}

.empty {
    color: #444;
}
</style>