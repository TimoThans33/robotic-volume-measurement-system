import sys
import os
import time
import faulthandler

faulthandler.enable()
# print(os.path.join(os.getcwd(), "..", ".."))
# sys.path.insert(0,"/home/thijs/miniconda3/lib")
sys.path.insert(0,os.path.join(os.getcwd(), "..", ".."))

import tjess.transport as tt
from tjess.transport.decorators import request_callback, subscribe_callback,response_callback

@subscribe_callback
def node1ServiceSimpleResponse(rep):
  print(rep)


if __name__ == "__main__":
  node2 = tt.Node("tjess", "node2")

  print("created node")
  node2.responseFunction(tt.Scope.HOST, "node1ServiceResponse", node1ServiceSimpleResponse )
  print("created remote function")

  print("running forever...")
  count = 0
  while(True):
    if count == 10:
      print("sending request")
      node2.request(tt.Scope.HOST, "node1", "node1Service", "Hooooi", "node1ServiceResponse")
      count = 0
    node2.spinOnce()
    time.sleep(0.001)
    count += 1