<script lang="ts" setup>
import { useGamepadWS } from '@/composeables/useGamepadWS'
import { onMounted, onUnmounted, ref } from 'vue'
import { useGamepad } from '@vueuse/core'
import { computed } from 'vue'
import { useRcControl } from '@/stores/rcControlStore.ts'
import Button from '@/components/ui/button/Button.vue'
import { PanelBottomClose, PanelBottomOpen, PanelTopOpen } from '@lucide/vue'
import CameraStream from '@/components/custom components/CameraStream.vue'

const rcControlStore = useRcControl()

const sendetLogs = ref<string[]>([])
const receivedLogs = ref<string[]>([])
const maxThrottle = computed(() => rcControlStore.throttleGears[rcControlStore.throttleIndex])
const calibrationSteering = computed(() => rcControlStore.steeringOffset)

const gamepadIndex = ref<number | null>(null)
let animationFrameId: number | null = null

const { isSupported, gamepads } = useGamepad()
const gamepad = computed(() => gamepads.value.find(g => g.mapping === 'standard'))
const { connected, sendControl, lastMessage } = useGamepadWS(import.meta.env.VITE_PI_URL)

const reverse = ref(0)
const throttle = ref(0)
const steering = ref(0)

let lastSend = 0
const SEND_RATE = 30 // Hz

onMounted(() => {
    addAllEventListeners()
})

onUnmounted(() => {
    if (animationFrameId) cancelAnimationFrame(animationFrameId)
})

function pollGamepad() {
    const now = performance.now()

    if (now - lastSend > 1000 / SEND_RATE) {
        lastSend = now

        const gp = navigator.getGamepads()[gamepadIndex.value!]
        if (!gp) return

        let steering = gp.axes[0] ?? 0              // Linker Stick
        let forward = gp.buttons[7]?.value ?? 0   // R2
        let reverse = gp.buttons[6]?.value ?? 0   // L2
        let calLeft = gp.buttons[14]?.value ?? 0
        let calRight = gp.buttons[15]?.value ?? 0
        let throttle = 0

        if (gp.buttons[6]?.pressed) {
            forward = 0
        }

        if (reverse > 0.2) {
            throttle = -reverse * (rcControlStore.maxThrottle / 100)
        } else {
            throttle = forward * (rcControlStore.maxThrottle / 100)
        }

        steering = rcControlStore.applySteeringOffset(steering)

        setReactives(throttle, steering)
        buttonEventListener(gp)
        logGamepadValues(throttle, steering)

        sendControl(steering, throttle)

        //console.log(imageSrc)
    }
    animationFrameId = requestAnimationFrame(() => pollGamepad())
}


function setReactives(throttlePar: number, steeringPar: number) {
    reverse.value = -throttlePar
    throttle.value = throttlePar
    steering.value = steeringPar
}

function buttonEventListener(gp: Gamepad) {
    buttonLogger(gp)
    rcControlStore.handleButtonL1(gp)
    rcControlStore.handleButtonR1(gp)
    rcControlStore.handleButtonLeft(gp)
    rcControlStore.handleButtonRight(gp)
}

function buttonLogger(gp: Gamepad) {
    gp.buttons.forEach((button, index) => {
        if (button.pressed) {
            console.log(`Pressed button ${index}`)
        }
    })
}

function logGamepadValues(throttle: number, steering: number) {
    sendetLogs.value.push(`Steering: ${Math.round(steering * 100) / 100} || Throttle: ${Math.round(throttle * 100) / 100}`)
    if (lastMessage.value) {
        receivedLogs.value.push(`Steering: ${lastMessage.value.received_steering} ||  Throttle: ${lastMessage.value.received_throttle} `)
    }
    const logContainers = document.querySelectorAll(".log-box")

    scrollToBottom(logContainers)
}

function scrollToBottom(logContainers: NodeListOf<Element>) {
    logContainers.forEach(contaner => {
        if (contaner) {
            contaner.scrollTop = contaner.scrollHeight;
        }
    });
}

function addAllEventListeners() {
    window.addEventListener('gamepadconnected', (e) => {
        if (e.gamepad.id === "Wireless Controller (STANDARD GAMEPAD Vendor: 054c Product: 05c4)") {
            gamepadIndex.value = e.gamepad.index
            animationFrameId = requestAnimationFrame(() => pollGamepad())

        }
    })

    window.addEventListener('gamepaddisconnected', (e) => {
        console.log(`❌ Controller getrennt: "${e.gamepad.id}"`)
        gamepadIndex.value = null
        if (animationFrameId) cancelAnimationFrame(animationFrameId)
    })
}
</script>

<template>
    <div class="main-container">
        <div>
            <CameraStream></CameraStream>
        </div>
        <div class="throttle-container">
            <div class="max-throttle-control">
                <h3>Modis</h3>
                <div class="throttle-buttons">
                    <Button @click="rcControlStore.decreaseMaxThrottle()" id="gamepad-l1"
                        :disabled="maxThrottle === 33">
                        <PanelBottomClose />
                    </Button>
                    <p v-if="maxThrottle === 33" class="low-speed">Low</p>
                    <p v-if="maxThrottle === 66" class="mid-speed">Mid</p>
                    <p v-if="maxThrottle === 99" class="full-speed">Full</p>
                    <Button @click="rcControlStore.increaseMaxThrottle()" id="gamepad-r1"
                        :disabled="maxThrottle === 99">

                        <PanelBottomOpen />
                    </Button>
                </div>
            </div>

            <div class="throttle-display-container">
                <div class="bar-container">
                    <div class="bar reverse" :style="{ height: reverse * 100 + '%' }"></div>
                </div>

                <div class="bar-container">
                    <div class="bar forward" :style="{ height: throttle * 100 + '%' }"></div>
                </div>

                <div class="steering-bar">
                    <div class="dot" :style="{ left: (-steering + 1) * 50 + '%' }"></div>
                </div>
            </div>
            <div class="calibration-container">
                <h3>Lenkung Offset</h3>
                <div class="calibration-control-container">
                    <div class="calibration-controls">
                        <Button @click="rcControlStore.decreaseSteeringOffset()">◀</Button>
                        <span class="offset-value" :class="{
                            'offset-positive': rcControlStore.steeringOffset > 0,
                            'offset-negative': rcControlStore.steeringOffset < 0,
                            'offset-zero': rcControlStore.steeringOffset === 0
                        }">
                            {{ calibrationSteering > 0 ? '+' : '' }}{{ calibrationSteering.toFixed(2) }}
                        </span>
                        <Button @click="rcControlStore.increaseSteeringOffset()">▶</Button>
                    </div>
                    <Button @click="rcControlStore.resetSteeringOffset()" class="reset-btn">Reset</Button>
                </div>
            </div>
        </div>
        <div class="status-row">
            <p v-if="gamepadIndex === null" class="hint">
                Controller verbinden und eine Taste drücken...
            </p>
            <p v-else class="connected">Controller aktiv (Index {{ gamepadIndex }})</p>

            <p :class="connected ? 'ws-connected' : 'ws-disconnected'">
                WebSocket: {{ connected ? '🟢 verbunden' : '🔴 getrennt' }}
            </p>
        </div>
        <div class="logger-container">
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

    </div>
</template>

<style scoped>
.main-container {
    font-family: monospace;
    padding: 2rem;
    width: 100%;
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

.logger-container {
    display: flex;
    flex-direction: row;
    gap: 12px;
    max-height: 50px;

    >div {
        width: 100%;
    }
}

.log-box {
    width: 100%;
    margin-top: 1rem;
    background: #111;
    color: #0f0;
    padding: 1rem;
    border-radius: 8px;
    height: 100%;
    overflow-y: auto;
    font-size: 13px;
    overflow: hidden;
}

.log-line {
    padding: 2px 0;
    border-bottom: 1px solid #1a1a1a;
}

.empty {
    color: #444;
}

.throttle-container {
    display: flex;
    flex-direction: row;
    justify-content: center;
    gap: 100px;
    border-top: 1px solid grey;
    border-bottom: 1px solid grey;
    padding: 12px 22px;
}

.max-throttle-control {

    display: flex;
    align-items: center;
    justify-content: space-evenly;
    flex-direction: column;
    text-align: center;

    >.throttle-buttons {

        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: center;
        gap: 18px;
        width: 100%;

        >p {
            min-width: 100px;
            font-size: 18px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            border: 2px solid transparent;
            padding: 6px 18px;
            border-radius: 8px;
        }
    }
}

.throttle-display-container {
    display: flex;
    gap: 22px;
    align-items: flex-end;

}

.bar-container {
    width: 30px;
    height: 120px;
    background: #222;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: flex-end;
}

.bar {
    width: 100%;
    transition: height 0.05s linear;
}

.forward {
    background: limegreen;
}

.reverse {
    background: red;
}

.steering-bar {
    width: 160px;
    height: 20px;
    background: #222;
    border-radius: 999px;
    position: relative;
}

.dot {
    width: 12px;
    height: 12px;
    background: white;
    border-radius: 50%;
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    transition: left 0.05s linear;
}

.low-speed {
    border-color: green !important;

    background-color: rgba(0, 128, 0, 0.2);
}

.mid-speed {
    border-color: yellow !important;

    background-color: rgba(255, 255, 0, 0.2);
}

.full-speed {
    border-color: red !important;

    background-color: rgba(255, 0, 0, 0.2);
}

.calibration-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-evenly;
    gap: 8px;
}

.calibration-control-container {
    display: flex;
    flex-direction: row;
    gap: 20px;
}

.calibration-controls {
    display: flex;
    align-items: center;
    gap: 12px;
}

.offset-value {
    min-width: 60px;
    text-align: center;
    font-size: 20px;
    font-weight: bold;
    font-family: monospace;
}

.offset-positive {
    color: #22c55e;
}

.offset-negative {
    color: #ef4444;
}

.offset-zero {
    color: #888;
}

.calibration-hint {
    font-size: 11px;
    color: #555;
}

.reset-btn {
    font-size: 12px;
}
</style>