import asyncio
import json

from websockets.asyncio.client import connect


async def main() -> None:
    async with connect("ws://127.0.0.1:8010/v1/tts/stream") as ws:
        await ws.send(json.dumps({"type": "start", "language": "Spanish", "num_step": 16, "format": "pcm16"}))
        print(await ws.recv())
        await ws.send(json.dumps({"type": "text", "text": "Hola mundo. Esto está saliendo por WebSocket."}))
        await ws.send(json.dumps({"type": "flush"}))
        while True:
            message = await ws.recv()
            print(message)
            if json.loads(message).get("type") == "done":
                break


if __name__ == "__main__":
    asyncio.run(main())
