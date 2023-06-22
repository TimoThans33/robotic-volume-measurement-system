#!/usr/bin/python3
import asyncio
from aiohttp import web

from app.mongodb import MDBclient
import aiohttp_cors
from bson import json_util
from datetime import datetime, timedelta
import pandas

"""
    HTTPserver class is used to create a web server that can be used to dump data from the MongoDB database.\
    - The server is created with the aiohttp.web module.
    - The server is started with the start() method.
    - The server is stopped with the stop() method.
    - The server is configured to accept CORS requests from any origin.
    - The server is configured to accept GET requests on the following endpoints:
        - /dumppayload
        - /dumpvolumes
        - /dumpweights
        - /dumpvolumetrics
        - /dumplectordata
"""
class HTTPserver(object):
    def __init__(self, ip_addr, port, custom_connection_string):
        self.loop = asyncio.get_event_loop()
        self.ip = ip_addr
        self.port = port
        mongo_connection_string = custom_connection_string
        self.mongo_client = MDBclient(mongo_connection_string)
        
        self.app = web.Application()
        self.app.router.add_get("/dumppayload", self.dumppayload_handle)
        self.app.router.add_get('/dumpvolumes', self.dumpvolumes_handle)
        self.app.router.add_get('/dumpweights', self.dumpweights_handle)
        self.app.router.add_get('/dumpvolumetrics', self.dumpvolumetrics_handle)
        self.app.router.add_get('/dumplectordata', self.dumplector_handle)

        self.setup_cors()

        self.runner = web.AppRunner(self.app)
        self.loop.create_task(self.setup())

    async def dumplector_handle(self, request):
        collection = self.mongo_client.get_collection("sorting-data", "payload")
        items = collection.find({
            "type": "piece_at_lector",
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))}
        })
        df = pandas.DataFrame(list(items))
        if not df.empty:
            df = df.drop(columns=["_id", "type", "jpg_files", "xml_files"], errors="ignore")
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(x))
        return web.Response(text="{0}".format(df.to_markdown()))
    
    async def dumppayload_handle(self, request):
        collection = self.mongo_client.get_collection("sorting-data", "payload")
        items = collection.find({
            "type": "piece_on_robot",
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))}
        })
        df = pandas.DataFrame(list(items))
        if not df.empty:
            df = df.drop(columns=["_id", "type", "date", "timestamp", "name", "sender", "elapsed_time", "start_time", "input"], errors="ignore")
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(x))
        return web.Response(text="{0}".format(df.to_markdown()))


    async def dumpvolumes_handle(self, request):
        collection = self.mongo_client.get_collection("sorting-data", "payload")
        items = collection.find({
            "type": "piece_at_dimensioner",
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))}
        })
        df = pandas.DataFrame(list(items))
        if not df.empty:
            df = df.drop(columns=["_id", "type"], errors="ignore")
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(x))        
        return web.Response(text="{0}".format(df.to_markdown()))
    
    async def dumpweights_handle(self, request):
        collection = self.mongo_client.get_collection("sorting-data", "dropoffs")
        items = collection.find({
            "type": "piece_at_output",
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))}
        })
        df = pandas.DataFrame(list(items))
        if not df.empty:
            df = df.drop(columns=["_id", "type", "date", "name", "sender", "cell", "volume", "battery_percentage", "input"], errors="ignore")
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(x))        
        return web.Response(text="{0}".format(df.to_markdown()))
    
    async def dumpvolumetrics_handle(self, request):
        collection = self.mongo_client.get_collection("sorting-data", "payload")
        dimensioned_items = collection.find({
            "type": "piece_dimensioned",
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))},
        })
        df = pandas.DataFrame(list(dimensioned_items))
        if not df.empty:
            df = df.drop(columns=["_id", "type"], errors="ignore")
        df["time"] = df["time"].apply(lambda x: datetime.fromtimestamp(x))        
        return web.Response(text="{0}".format(df.to_markdown()))
    
    def setup_cors(self):
        cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        cors_config = {
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        }
        for route in list(self.app.router.routes()):
            cors.add(route, cors_config)

    async def setup(self):
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.ip, self.port)
        await self.site.start()

    async def start(self):\
        await self.site.start()
    
    async def stop(self):
        await self.runner.cleanup()
    
    def run(self):
        # blocking call
        print("Running HTTP server on {0}:{1}".format(self.ip, self.port), flush=True)
        web.run_app(self.app)