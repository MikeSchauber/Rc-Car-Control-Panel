<script lang="ts" setup>
import { useGamepadWS } from '@/composeables/useGamepadWS'
import { onMounted, onUnmounted, ref } from 'vue'
import Button from '../ui/button/Button.vue'
import { mapGamepadToXbox360Controller, useGamepad } from '@vueuse/core'
import { computed } from 'vue'

const sendetLogs = ref<string[]>([])
const receivedLogs = ref<string[]>([])
const maxThrottle = ref<number>(100)

const gamepadIndex = ref<number | null>(null)
let animationFrameId: number | null = null



const { isSupported, gamepads } = useGamepad()
const gamepad = computed(() => gamepads.value.find(g => g.mapping === 'standard'))
const controller = mapGamepadToXbox360Controller(gamepad)

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
    addAllEventListeners()
})

onUnmounted(() => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId)
})

function addAllEventListeners() {
    window.addEventListener('gamepadconnected', (e) => {
        if (e.gamepad.index === 0) {
            gamepadIndex.value = e.gamepad.index
            animationFrameId = requestAnimationFrame(() => pollGamepad())

        }
        // console.log(`✅ Controller verbunden: "${e.gamepad.id}"`)
        // const message = `   Achsen: ${e.gamepad.axes.length} | Buttons: ${e.gamepad.buttons.length}`
        // console.log(animationFrameId)
    })

    window.addEventListener('gamepaddisconnected', (e) => {
        console.log(`❌ Controller getrennt: "${e.gamepad.id}"`)
        gamepadIndex.value = null
        if (animationFrameId) cancelAnimationFrame(animationFrameId)
    })
}
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

        <div class="max-throttle-control">

            <Button id="gamepad-l1" :disabled="maxThrottle === 33">
                L1
            </Button>
            <p :class="maxThrottle === 33
                ? 'low-speed'
                : maxThrottle === 66
                    ? 'mid-speed'
                    : maxThrottle === 100
                        ? 'high-speed'
                        : ''
                "> {{ maxThrottle }}% </p>
            <Button id="gamepad-r1" :disabled="maxThrottle === 100">
                R1
            </Button>
        </div>

        <div>
            <h2>Gesendete Werte: </h2>
            <div class=" log-box">
                <div v-for="(line, i) in sendetLogs" :key="i" class="log-line">{{ line }}</div>
                <div v-if="sendetLogs.length === 0" class="empty">Keine Eingaben...</div>
            </div>
        </div>

        <div>
            <h2>Empfangene Werte: </h2>
            <div class="log-box">
                <div v-for="(line, i) in receivedLogs" :key="i" class="log-line">{{ line }}</div>
                <div v-if="receivedLogs.length === 0" class="empty">Keine Eingaben...</div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.container {
    font-family: monospace;
    padding: 2rem;
    max-width: 700px;
    display: flex;
    flex-direction: column;
    gap: 20px;
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

.max-throttle-control {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    width: 100%;
    max-width: 180px;

    >p {
        display: flex;
        align-items: center;
        font-size: 20px;
        font-weight: bold;
    }
}

.low-speed {
    border-color: green;
    color: green;
}

.mid-speed {
    border-color: yellow;
    color: yellow;
}

.full-speed {
    border-color: red;
    color: red;
}
</style>