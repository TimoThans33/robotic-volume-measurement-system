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



if __name__ == "__main__":
  node2 = tt.Node("tjess", "node2")

  print("running forever...")
  count = 0
  while(True):
    if count == 10:
      print("sending request")
      node2.publish(tt.Scope.HOST, "publisher", "pubHooooi")
      count = 0
    node2.spinOnce()
    time.sleep(0.1)
    count += 1