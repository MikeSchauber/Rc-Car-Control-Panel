<script lang="ts" setup>
import { useGamepadWS } from '@/composeables/useGamepadWS'
import { onMounted, onUnmounted, ref } from 'vue'

const sendetLogs = ref<string[]>([])
const receivedLogs = ref<string[]>([])

const gamepadIndex = ref<number | null>(null)
let animationFrameId: number | null = null

const { connected, sendControl, lastMessage } = useGamepadWS(import.meta.env.VITE_PI_URL)

let lastSend = 0
const SEND_RATE = 30 // Hz

function pollGamepad() {
    const now = performance.now()

    if (now - lastSend > 1000 / SEND_RATE) {
        lastSend = now

        const gp = navigator.getGamepads()[gamepadIndex.value!]
        if (!gp) return

        let steering = gp.axes[0] ?? 0 // Linker Stick
        const forward = gp.buttons[7]?.value ?? 0 // R2
        const reverse = gp.buttons[6]?.value ?? 0 // L2

        let throttle = 0



        if (reverse > 0.2) {
            throttle = -reverse
        } else {
            throttle = forward
        }

        sendetLogs.value.push(`Throttle: ${Math.round(throttle * 100) / 100} || Steering: ${Math.round(steering * 100) / 100}`)
        scollToBottom()

        if (lastMessage.value) {
            receivedLogs.value.push(`Throttle: ${lastMessage.value.received_throttle} || Steering: ${lastMessage.value.received_steering}`)
        }


        sendControl(steering, throttle)
    }
    animationFrameId = requestAnimationFrame(() => pollGamepad())
}

function scollToBottom() {
    const logContainers = document.querySelectorAll(".log-box")

    logContainers.forEach(contaner => {
        if (contaner) {
            contaner.scrollTop = contaner.scrollHeight;
        }
    });
}

onMounted(() => {
    window.addEventListener('gamepadconnected', (e) => {
        gamepadIndex.value = e.gamepad.index
        animationFrameId = requestAnimationFrame(() => pollGamepad())

        // console.log(`✅ Controller verbunden: "${e.gamepad.id}"`)
        // const message = `   Achsen: ${e.gamepad.axes.length} | Buttons: ${e.gamepad.buttons.length}`
        // console.log(animationFrameId)
    })

    window.addEventListener('gamepaddisconnected', (e) => {
        console.log(`❌ Controller getrennt: "${e.gamepad.id}"`)
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

        <h2>Gesendete Werte: </h2>
        <div class="log-box" >
            <div v-for="(line, i) in sendetLogs" :key="i" class="log-line">{{ line }}</div>
            <div v-if="sendetLogs.length === 0" class="empty">Keine Eingaben...</div>
        </div>

        <h2>Empfangene Werte: </h2>
        <div class="log-box" >
            <div v-for="(line, i) in receivedLogs" :key="i" class="log-line">{{ line }}</div>
            <div v-if="receivedLogs.length === 0" class="empty">Keine Eingaben...</div>
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