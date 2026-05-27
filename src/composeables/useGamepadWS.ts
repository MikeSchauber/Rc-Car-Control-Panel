// composables/useGamepadWS.ts
import { ref, onUnmounted } from 'vue'

export function useGamepadWS(url: string) {
    const ws = ref<WebSocket | null>(null)
    const connected = ref(false)
    const lastMessage = ref<any>(null)

    function connect() {
        ws.value = new WebSocket(url)

        ws.value.onopen = () => {
            connected.value = true
            console.log('WebSocket verbunden')
        }

        ws.value.onclose = () => {
            connected.value = false
            console.log('WebSocket getrennt — reconnect in 2s')
            setTimeout(connect, 2000)
        }

        ws.value.onmessage = (event) => {
            if (typeof event.data == "string") {
                const data = JSON.parse(event.data)
                lastMessage.value = data
            }
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