import sys
import os
import time
import faulthandler
import json
import asyncio
import concurrent.futures
import random
faulthandler.enable()

from tjess import transport
from tjess.transport.decorators import subscribe_callback_method, request_callback_method, request_callback, subscribe_callback
from tjess.transport import Peer


class tjess_node(object):
    def __init__(self, name, port, peers=[]):        
        self.scope = "pv"
        self.name = name
        
        self.tjess_ip = "0.0.0.0"
        self.tjess_port = port

        self.response_callback = "response_callback"
        self.request_callback = "request_callback"

        self.tjess_libname = "libtjess-transport-dll.so"
        if getattr(sys, 'frozen', False):
            self.libpath = os.path.join(os.path.dirname(sys.executable), self.tjess_libname)
        else:
            self.libpath = "/usr/local/lib/tjess/"+self.tjess_libname

        self.node = transport.Node(self.scope, self.name, libpath=self.libpath)
        self.node.setIp("0.0.0.0")
        self.node.setPort(int(6025))
        
        for peer in peers:
            peer.router_endpoints = "tcp://{}:{}".format(peer.ip, str(peer.port))
            peer.publisher_endpoints = "tcp://{}:{}".format(peer.ip, str(peer.port))
            self.node.addPeer(peer)
        
        self.loop = asyncio.get_event_loop()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.loop.run_in_executor(self.executor, self.blocking_spin_)

    def response_callback(self, response):
        return response

    def blocking_spin_(self):
        while(True):
            self.node.spinOnce()
            time.sleep(0.001)

    def sendrequest(self, peer_name, method, data, response=False):
        if response:
            self.node.request(transport.Scope.HOST, peer_name, method, data, self.response_callback)        
        else:
            self.node.request(transport.Scope.HOST, peer_name, method, data, "\0")

async def requester(tjess_node: tjess_node):
    while True:
        print("sending request")
        tjess_node.sendrequest("res", "tester", "hello world!")
        await asyncio.sleep(5)

if __name__ == "__main__":
    peers = [Peer("pv", "res", "0.0.0.0", 6025)]
    test_instance = tjess_node("req", 5020, peers)
    print("running forever...")
    asyncio.run(requester(test_instance))