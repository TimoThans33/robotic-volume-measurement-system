#!/usr/bin/python3

import asyncio
import concurrent.futures
import pymongo
import pandas

"""
    MDBclient is a wrapper around pymongo.MongoClient:
        - It provides a non-blocking connect method and a poller that notifies subscribers of changes in the database
        - Subscribers are added with the add_subscriber method and removed with the remove_subscriber method
        - Subscribers are coroutines that take one argument, the document that was added to the database
        - The document is a python dictionary
"""
class MDBclient():
    def __init__(self, connection_string = "mongodb://localhost:27017"):
        self.connection_string = connection_string
        self.loop = asyncio.get_event_loop()
        self.db = None
        self.mongo_client = None
        self.is_connected = False
        self.subscribers = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.connect()
        self.loop.create_task(self.poller_())


    def blocking_connect_(self):
        self.mongo_client = pymongo.MongoClient(self.connection_string)
        try: 
            self.mongo_client.admin.command('ping')
            print("connected to mongodb server on: ", self.connection_string, "", flush=True)
            self.is_connected = True
        except:
            print("mongdb server not available on: ", self.connection_string, "", flush=True)
            self.is_connected = False
    
    def add_subscriber(self, db, topic, coroutine):
        if db not in self.subscribers:
            self.subscribers[db] = {}
        self.subscribers[db][topic] = coroutine
    
    def remove_subscriber(self, db, topic):
        del self.subscribers[db][topic]

    async def poller_(self):
        while self.is_connected == False:
            await asyncio.sleep(1)
            self.connect()
        collections = {}
        hashes = {}
        for db in self.subscribers:
            for topic in self.subscribers[db]:
                if db not in collections:
                    collections[db] = {}
                if topic not in collections[db]:
                    collections[db][topic] = self.get_collection("sorting-data", db)
        while True:
            await asyncio.sleep(1)
            for db in collections:
                for topic in collections[db]:
                    doc = collections[db][topic].find({"type": topic}).sort("_id", -1).limit(1)
                    doc = list(doc)
                    item = doc[0] if doc else None
                    new_hash = self.hash(item)
                    if item is not None:
                        if topic not in hashes:
                            hashes[topic] = new_hash
                        elif new_hash != hashes[topic]:
                            hashes[topic] = new_hash
                            self.loop.create_task(self.subscribers[db][topic](item))
    
    def hash(self, doc):
        df = pandas.DataFrame([doc])
        return pandas.util.hash_pandas_object(df).sum()
    
    def create_collection(self, db_name, collection_name):
        db = self.get_db(db_name)
        db.create_collection(collection_name)
        
    def connect(self):
        self.loop.run_in_executor(self.executor, self.blocking_connect_)
    
    def get_db(self, db_name):
        return self.mongo_client[db_name]
    
    def get_collection(self, db_name, collection_name):
        db = self.get_db(db_name)
        try:
            db.validate_collection(collection_name)
        except pymongo.errors.OperationFailure:
            db.create_collection(collection_name)
        return db.get_collection(collection_name)