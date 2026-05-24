import asyncio
import websockets
import json
import random
import os

# Хранилище комнат
rooms = {}

async def handler(websocket, path):
    room_id = None
    role = None

    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")

            if action == "create":
                room_id = data.get("room_id", "")
                if not room_id or room_id in rooms:
                    await websocket.send(json.dumps({"type": "error", "msg": "Комната занята"}))
                    continue
                seed = random.randint(1, 1000000)
                rooms[room_id] = {"host": websocket, "guest": None, "seed": seed, "started": False}
                role = "host"
                await websocket.send(json.dumps({"type": "created", "room_id": room_id, "seed": seed}))
                print(f"Комната {room_id} создана, seed={seed}")

            elif action == "join":
                room_id = data.get("room_id", "")
                if room_id not in rooms:
                    await websocket.send(json.dumps({"type": "error", "msg": "Комната не найдена"}))
                    continue
                if rooms[room_id]["guest"] is not None:
                    await websocket.send(json.dumps({"type": "error", "msg": "Комната полная"}))
                    continue
                rooms[room_id]["guest"] = websocket
                role = "guest"
                seed = rooms[room_id]["seed"]
                await websocket.send(json.dumps({"type": "joined", "room_id": room_id, "seed": seed}))
                host_ws = rooms[room_id]["host"]
                await host_ws.send(json.dumps({"type": "player_joined"}))
                print(f"Игрок присоединился к {room_id}")

            elif action == "start":
                if room_id and room_id in rooms and role == "host":
                    rooms[room_id]["started"] = True
                    guest_ws = rooms[room_id]["guest"]
                    if guest_ws:
                        await guest_ws.send(json.dumps({"type": "game_start"}))
                    await websocket.send(json.dumps({"type": "game_start"}))
                    print(f"Игра {room_id} началась")

            elif action == "input":
                if room_id and room_id in rooms:
                    room = rooms[room_id]
                    target = room["guest"] if role == "host" else room["host"]
                    if target:
                        await target.send(json.dumps({
                            "type": "input",
                            "lane": data.get("lane"),
                            "nitro": data.get("nitro"),
                            "x": data.get("x"),
                            "finished": data.get("finished"),
                            "finish_time": data.get("finish_time")
                        }))

            elif action == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if room_id and room_id in rooms:
            room = rooms[room_id]
            if role == "host":
                if room["guest"]:
                    try:
                        await room["guest"].send(json.dumps({"type": "host_left"}))
                    except:
                        pass
                del rooms[room_id]
                print(f"Комната {room_id} закрыта")
            elif role == "guest":
                room["guest"] = None
                room["started"] = False
                try:
                    await room["host"].send(json.dumps({"type": "guest_left"}))
                except:
                    pass

# Replit использует переменную окружения PORT
PORT = int(os.environ.get("PORT", 8765))

start_server = websockets.serve(handler, "0.0.0.0", PORT)
print(f"Сервер запущен на порту {PORT}")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
