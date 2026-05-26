
import asyncio
import websockets
import json



async def handler(ws):
    print("Client connected")

    async for msg in ws:
        try:
            data = json.loads(msg)

            throttle = data.get("throttle", 0)
            steering = data.get("steering", 0)

            print(f"Throttle: {throttle} | Steering: {steering}")

            dataJson = getDataJson(throttle, steering)
            await ws.send(dataJson)

        except Exception as e:
            print("Error:", e)



async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket running on port 8765")
        await asyncio.Future()



def getDataJson(throttle, steering):
    return json.dumps({
        "status": "ok",
        "received_throttle": throttle,
        "received_steering": steering
    })



asyncio.run(main())

