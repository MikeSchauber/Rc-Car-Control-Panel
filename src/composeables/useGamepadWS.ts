// composables/useGamepadWS.ts
import { ref, onUnmounted } from 'vue'

export function useGamepadWS(url: string) {
    const ws = ref<WebSocket | null>(null)
    const connected = ref(false)

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

        ws.value.onerror = (e) => console.error('WS Fehler:', e)
    }

    function sendControl(steering: number, throttle: number) {
        if (ws.value?.readyState === WebSocket.OPEN) {
            ws.value.send(JSON.stringify({
                steering: parseFloat(steering.toFixed(3)),
                throttle: parseFloat(throttle.toFixed(3))
            }))
        }
    }

    // function response() {
    //     if (ws.value) {
    //         const data: any = ws.value.onmessage = (event) => {
    //             try {
    //                 const data = JSON.parse(event.data)
    //                 return data
    //             } catch (error) {
    //                 console.error('Invalid WS response:', error)
    //             }

    //             // "status": "ok",
    //             // "received_throttle": throttle,
    //             // "received_steering": steering

    //             return data
    //         }
    //         return data
    //     }

    // }

    connect()
    onUnmounted(() => ws.value?.close())

    return { connected, sendControl }

}