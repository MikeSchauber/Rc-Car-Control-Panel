<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

const mediamtxBase = import.meta.env.VITE_WEB_RTC_STREAM.replace(/\/[^/]*\/?$/, '')
const path = 'cam_with_audio'

let pc: RTCPeerConnection | null = null
let statsInterval: ReturnType<typeof setInterval> | null = null
let lastFrames = 0
let stallCount = 0
let latencyHighCount = 0
const MAX_STALL = 3
const MAX_LATENCY_MS = 3000
const MAX_LATENCY_COUNT = 2 // 2x hintereinander zu hoch → reconnect

const videoRef = ref<HTMLVideoElement | null>(null)
const connected = ref(false)
const latency = ref(0)

let prevJitterDelay = 0
let prevJitterCount = 0

async function connect() {
  disconnect()

  try {
    pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    })

    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })

    pc.ontrack = (evt) => {
      if (videoRef.value && evt.streams[0]) {
        videoRef.value.srcObject = evt.streams[0]
      }
    }

    pc.oniceconnectionstatechange = () => {
      const state = pc!.iceConnectionState
      console.log('[WebRTC] ICE:', state)

      if (state === 'disconnected' || state === 'failed') {
        connected.value = false
        setTimeout(connect, 1000)
      } else if (state === 'connected') {
        connected.value = true
        stallCount = 0
        latencyHighCount = 0
        prevJitterDelay = 0
        prevJitterCount = 0
        startStallDetection()
      }
    }

    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    await new Promise<void>((resolve) => {
      if (pc!.iceGatheringState === 'complete') return resolve()
      pc!.onicegatheringstatechange = () => {
        if (pc!.iceGatheringState === 'complete') resolve()
      }
      setTimeout(resolve, 3000)
    })

    const res = await fetch(`${mediamtxBase}/${path}/whep`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/sdp' },
      body: pc.localDescription!.sdp
    })

    if (!res.ok) throw new Error(`WHEP ${res.status}`)

    const answer = await res.text()
    await pc.setRemoteDescription({ type: 'answer', sdp: answer })

  } catch (err) {
    console.error('[WebRTC]', err)
    setTimeout(connect, 2000)
  }
}

function startStallDetection() {
  stopStallDetection()
  lastFrames = 0
  stallCount = 0
  latencyHighCount = 0

  statsInterval = setInterval(async () => {
    if (!pc || pc.connectionState === 'closed') return

    const stats = await pc.getStats()
    let currentFrames = 0

    stats.forEach((report: any) => {
      if (report.type === 'inbound-rtp' && report.kind === 'video') {
        currentFrames = report.framesReceived || 0

        // Latenz aus Jitter Buffer berechnen
        const jd = report.jitterBufferDelay || 0
        const jc = report.jitterBufferEmittedCount || 0
        const deltaDelay = jd - prevJitterDelay
        const deltaCount = jc - prevJitterCount

        if (deltaCount > 0) {
          latency.value = Math.round((deltaDelay / deltaCount) * 1000)
          console.log(`[WebRTC] Latenz: ${latency.value}ms`)
        }

        prevJitterDelay = jd
        prevJitterCount = jc
      }
    })

    // Stall Check
    if (currentFrames === lastFrames && lastFrames > 0) {
      stallCount++
      console.warn(`[WebRTC] Stall ${stallCount}/${MAX_STALL}`)
      if (stallCount >= MAX_STALL) return connect()
    } else {
      stallCount = 0
    }

    // Latenz Check
    if (latency.value > MAX_LATENCY_MS) {
      latencyHighCount++
      console.warn(`[WebRTC] Latenz zu hoch: ${latency.value}ms (${latencyHighCount}/${MAX_LATENCY_COUNT})`)
      if (latencyHighCount >= MAX_LATENCY_COUNT) return connect()
    } else {
      latencyHighCount = 0
    }

    lastFrames = currentFrames
  }, 2000)
}

function stopStallDetection() {
  if (statsInterval) {
    clearInterval(statsInterval)
    statsInterval = null
  }
}

function disconnect() {
  stopStallDetection()
  if (pc) {
    pc.close()
    pc = null
  }
  connected.value = false
}

onMounted(connect)
onUnmounted(disconnect)
</script>

<template>
  <div class="frame-container">
    <video ref="videoRef" autoplay playsinline />
    <div v-if="!connected" class="reconnecting">🔄 Verbinde...</div>
    <div class="latency-badge" :class="{ warn: latency > 1000, critical: latency > MAX_LATENCY_MS }">
      {{ latency }}ms
    </div>
  </div>
</template>

<style scoped>
.frame-container {
  display: flex;
  justify-content: center;
  position: relative;
}

.frame-container > video {
  width: 1200px;
  height: 676px;
  border-radius: 8px;
  box-shadow: 0px 0px 16px 0px rgba(0, 0, 0, 0.648);
  background: #000;
  object-fit: contain;
}

.reconnecting {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 1.2rem;
  background: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 8px;
}

.latency-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  color: #0f0;
  font-size: 0.85rem;
  font-family: monospace;
  background: rgba(0, 0, 0, 0.5);
  padding: 4px 10px;
  border-radius: 6px;
}

.latency-badge.warn {
  color: #ffa500;
}

.latency-badge.critical {
  color: #ff3333;
}
</style>