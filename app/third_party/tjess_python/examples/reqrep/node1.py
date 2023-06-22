import sys
import os
import time
from ctypes import *
import faulthandler
faulthandler.enable()
# print(os.path.join(os.getcwd(), "..", ".."))
# sys.path.insert(0,"/home/thijs/miniconda3/lib")
sys.path.insert(0,os.path.join(os.getcwd(), "..", ".."))
import tjess.transport as tt
from tjess.transport.decorators import request_callback, subscribe_callback



@request_callback
def node1ServiceSimple(req):
  print(req)
  rep ="Node 1 Response!"
  return rep
  # s = create_string_buffer('hoi node2'.encode("utf-8"))
  # rep = cast(s, POINTER(c_char))
  # print(d)
  # rep = POINTER(s)



if __name__ == "__main__":
  node1 = tt.Node("tjess", "node1")

  print("created node")
  node1.remoteFunction(tt.Scope.HOST, "node1Service", node1ServiceSimple )
  print("created remote function")

  print("running forever...")
  while(True):
    node1.spinOnce()
    time.sleep(0.001)