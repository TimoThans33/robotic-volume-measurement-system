#!/usr/bin/python3

import asyncio
import xml.etree.ElementTree as ET
import os
import sys

import faulthandler
from app.third_party.tjess_python.tjess import transport
from app.third_party.tjess_python.tjess.transport.decorators import subscribe_callback_method, request_callback, response_callback
from app.third_party.tjess_python.tjess.transport.peer import Peer
faulthandler.enable()

"""
    XMLconnector is a wrapper around asyncio.start_server:
        - It provides a non-blocking serve method and a handle_connection method that notifies subscribers of incoming xml messages
        - Subscribers are added with the add_subscriber method and removed with the remove_subscriber method
"""
class XMLconnector():
    def __init__(self, host, port, print_raw_xml=False):
        self.loop = asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.subscribers = {}
        self.print_raw_xml = print_raw_xml
        self.loop.create_task(self.serve())
    
    async def serve(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        print("serving on {}:{}".format(self.host, self.port), flush=True)
        async with server:
            await server.serve_forever()
    
    def add_subscriber(self, topic, coroutine):
        self.subscribers[topic] = coroutine
    
    def remove_subscriber(self, topic):
        del self.subscribers[topic]

    async def handle_connection(self, reader, writer):
        while True:
            data = await reader.read(4096)
            if data:
                if self.print_raw_xml:
                    print("raw xml message : ", data, flush=True)
                try:
                    root = ET.fromstring(data)
                    topic = root.attrib['Type']
                except ET.ParseError:
                    print("xml parse error", flush=True)
                    continue
                if topic in self.subscribers:
                    self.loop.create_task(self.subscribers[topic](data))
            else:
                break
        print("connection closed")
        writer.close()
        await writer.wait_closed()
"""
    TJESSconnector is a wrapper around tjess.transport.Node:
        - It provides a non-blocking request sender and a response handler
"""
class TJESSconnector():
    def __init__(self, scope, name, port, peers=[]):
        self.scope = scope
        self.name = name
        
        self.tjess_ip = "0.0.0.0"
        self.tjess_port = port

        self.response_callback = "response_callback"
        self.request_callback = "request_callback"

        self.tjess_libname = "libtjess-transport-dll.so"
        
        if getattr(sys, 'frozen', False):
            self.libpath = os.path.join(getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__))), self.tjess_libname)
        else:
            self.libpath = "/usr/local/lib/tjess/"+self.tjess_libname

        self.node = transport.Node(self.scope, self.name, libpath=self.libpath)
        self.node.setIp(self.tjess_ip)
        self.node.setPort(self.tjess_port)

        for peer in peers:
            peer.router_endpoints = "tcp://{}:{}".format(peer.ip, str(peer.port))
            peer.publisher_endpoints = "tcp://{}:{}".format(peer.ip, str(peer.port))
            self.node.addPeer(peer)
        
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.spin())
    
    def response_callback(self, msg):
        return msg

    def sendrequest(self, peer_name, method, data, response=False):
        if response:
            self.node.request(transport.Scope.HOST, peer_name, method, data, self.response_callback)        
        else:
            self.node.request(transport.Scope.HOST, peer_name, method, data, "\0")

    async def spin(self):
        self.node.spinOnce()
        await asyncio.sleep(0.01)
        self.loop.create_task(self.spin())

"""
    TJESSpeer is a wrapper around tjess.transport.Peer:
        - It provides a simple way to create a peer object
"""
class TJESSpeer(object):
    def __init__(self, partition, name, ip, port):
        self.partition = partition
        self.name = name
        self.id = "{}_{}".format(partition, name)
        self.ip = str(ip)
        self.port = int(port)
        self.scope = transport.Scope.HOST
        self.status = transport.Status.DISCONNECTED