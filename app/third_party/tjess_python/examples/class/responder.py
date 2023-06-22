import sys
import os
import time
from ctypes import *
import faulthandler
faulthandler.enable()

import tjess.transport as tt
from tjess.transport.decorators import request_callback, subscribe_callback

@request_callback
def tester(req):
  print(req)

def get_path_to_tjess():
  tjess_libname = "libtjess-transport-dll.so"
  if getattr(sys, 'frozen', False):
      libpath = os.path.join(os.path.dirname(sys.executable), tjess_libname)
  else:
      libpath = "/usr/local/lib/tjess/"+tjess_libname
  return libpath

if __name__ == "__main__":
  node1 = tt.Node("pv", "res", get_path_to_tjess())
  node1.setIp("0.0.0.0")
  node1.setPort(int(6025))
  
  node1.remoteFunction(tt.Scope.HOST, "tester", tester)

  print("running forever...")
  while(True):
    node1.spinOnce()
    time.sleep(0.001)