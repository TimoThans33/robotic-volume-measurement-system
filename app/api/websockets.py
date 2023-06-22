import asyncio
import websockets

class QBWebsocket():
    def __init__(self, ip, port):
        self.loop = asyncio.get_event_loop()
        self.ip = ip
        self.port = port
        self.ws = None
        self.subscribers = {}
        self.loop.create_task(self.connect())

    async def connect(self):
        print("attempting to connect to websocket")
        async for websocket in websockets.connect("ws://{}:{}/ws".format(self.ip, self.port)):
            try:
                self.ws = websocket
                await self.ws_handler(websocket)
            except websockets.ConnectionClosed:
                print("connection closed")
                continue
            except Exception as e:
                print(e)
                continue

    def add_subscriber(self, topic, coroutine):
        self.subscribers[topic] = coroutine
    
    def remove_subscriber(self, topic):
        del self.subscribers[topic]

    async def ws_handler(self, websocket):
        async for msg in websocket:
            for topic, coroutine in self.subscribers.items():
                if topic in msg:
                    await coroutine(msg)