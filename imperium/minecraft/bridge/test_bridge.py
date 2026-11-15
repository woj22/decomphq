"""Vaccaria bridge - connection test.

Run in Termux:  python test_bridge.py
Then in Minecraft (cheats on):  /connect localhost:8000
Anything you type in chat is echoed back by the bridge.
"""
import asyncio
import json
import uuid

import websockets

PORT = 8000


def command(line):
    return json.dumps({"header": {"version": 1, "requestId": str(uuid.uuid4()), "messagePurpose": "commandRequest",
                                  "messageType": "commandRequest"},
                       "body": {"version": 1, "commandLine": line, "origin": {"type": "player"}}})


def tell(text):
    return command("tellraw @a " + json.dumps({"rawtext": [{"text": text}]}, ensure_ascii=False))


async def handler(ws, *_):
    print("Minecraft connected")
    await ws.send(json.dumps({"header": {"version": 1, "requestId": str(uuid.uuid4()), "messagePurpose": "subscribe",
                                         "messageType": "commandRequest"}, "body": {"eventName": "PlayerMessage"}}))
    await ws.send(tell("§6[Bridge]§r Connected! Say something in chat."))
    async for raw in ws:
        msg = json.loads(raw)
        h, b = msg.get("header", {}), msg.get("body", {})
        if h.get("eventName") == "PlayerMessage" and b.get("type") == "chat" and b.get("sender") != "External":
            print("%s: %s" % (b.get("sender"), b.get("message")))
            await ws.send(tell("§6[Bridge]§r I heard %s say: %s" % (b.get("sender"), b.get("message"))))
    print("Minecraft disconnected")


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print("Bridge running. In Minecraft type:  /connect localhost:%d" % PORT)
        await asyncio.Future()

asyncio.run(main())
