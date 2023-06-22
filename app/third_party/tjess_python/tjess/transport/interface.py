from ctypes import *
import os
import sys

TWO_CHAR_FUNC_FACTORY = CFUNCTYPE(c_char_p, POINTER(c_char), POINTER(c_char))
ONE_CHAR_FUNC_FACTORY = CFUNCTYPE(c_void_p, POINTER(c_char))

class Interface:
  def __init__(self, libpath="/usr/local/lib/tjess/libtjess-transport-dll.so"):
    self.__handle = cdll.LoadLibrary(libpath)
    self.__remote_function_handles_ = []

  def __del__(self):
    pass
    #_ctypes.dlclose(self.__handle)

  def close(self):
    pass
    # _ctypes.dlclose(self.__handle)
  
  def createNode(self, partition, name):
    if self.__handle.createNode(partition.encode("utf-8"), name.encode("utf-8") ):
      raise Exception("Failed to create tjess.transport.Node")

  def closeNode(self, _id):
    if self.__handle.close(_id.encode("utf-8")):
      raise Exception("Failed to close tjess.transport.Node")

  def getId(self, _id):
    out = c_char_p
    if self.__handle.getId(_id.encode("utf-8"), out):
      raise Exception("Failed to get node id")
    return cast(out, c_char_p).value.decode()

  def getPartition(self, _id):
    out = c_char_p
    if self.__handle.getPartition(_id.encode("utf-8"), out):
      raise Exception("Failed to get node partition")
    return cast(out, c_char_p).value.decode()

  def getName(self, _id):
    out = c_char_p
    if self.__handle.getName(_id.encode("utf-8"), out):
      raise Exception("Failed to node name")
    return cast(out, c_char_p).value.decode()

  def getPort(self, _id):
    out = c_ushort
    if self.__handle.getPort(_id.encode("utf-8"), byref(out)):
      raise Exception("Failed to get node base port")
    return out.value

  def setPort(self, _id, port):
    if self.__handle.setPort(_id.encode("utf-8"), byref(c_ushort(port))):
      raise Exception("Failed to set node base port")

  def getIp(self, _id):
    out = c_char_p
    if self.__handle.getIp(_id.encode("utf-8"), out):
      raise Exception("Failed get node IP")
    return cast(out, c_char_p).value.decode()

  def setIp(self, _id, ip):
    if self.__handle.setIp(_id.encode("utf-8"), ip.encode("utf-8")):
      raise Exception("Failed to set node IP")

  def getScope(self, _id):
    out = c_ubyte
    if self.__handle.getPort(_id.encode("utf-8"), byref(out)):
      raise Exception("Failed to get node scope")
    return out.value

  def setScope(self, _id, scope):
    if self.__handle.setPort(_id.encode("utf-8"), c_ubyte(scope) ):
      raise Exception("Failed to set node scope")

  def spinOnce(self, _id):
    id_p = _id.encode("utf-8")
    if self.__handle.spinOnce(id_p):
      raise Exception("Failed to spinOnce")
    del id_p

  def publish(self, _id, scope, topic, msg):
    if self.__handle.publish(_id.encode("utf-8"), byref(c_ubyte(scope)), topic.encode("utf-8"), msg.encode("utf-8")):
      raise Exception("Failed to publish on topic {}".format(topic))

  def request(self,_id, scope, peer_id,  remote_function_name, request, response_function_name=""):
    if self.__handle.request(_id.encode("utf-8"), byref(c_ubyte(scope)), peer_id.encode("utf-8"), remote_function_name.encode("utf-8"), request.encode("utf-8"), response_function_name.encode("utf-8")):
      raise Exception("Failed to request")

  def remoteFunction(self, _id, scope, command, func):
    c_func = TWO_CHAR_FUNC_FACTORY(func)
    self.__remote_function_handles_.append(c_func)
    if self.__handle.remoteFunction(_id.encode("utf-8"),byref(c_ubyte(scope)), command.encode("utf-8"), c_func ):
      raise Exception("Failed to create remote function")

  def responseFunction(self, _id, scope, command, func):
    c_func = ONE_CHAR_FUNC_FACTORY(func)
    self.__remote_function_handles_.append(c_func)
    if self.__handle.responseFunction(_id.encode("utf-8"),byref(c_ubyte(scope)), command.encode("utf-8"), c_func):
      raise Exception("Failed to create response function")

  def subscribe(self, _id, scope, topic, func):
    c_func = ONE_CHAR_FUNC_FACTORY(func)
    self.__remote_function_handles_.append(c_func)
    if self.__handle.subscribe(_id.encode("utf-8"),byref(c_ubyte(scope)), topic.encode("utf-8"), c_func):
      raise Exception("Failed to create subscriber")


  def createPeer(self, partition, name, ip, port):
    if self.__handle.createPeer(partition.encode("utf-8"), name.encode("utf-8"), ip.encode("utf-8"), byref(c_ushort(port))):
      raise Exception("Failed to create Peer")

  def addPeer(self, _id, peer_id):
    if self.__handle.addPeer(_id.encode("utf-8"), peer_id.encode("utf-8")):
      raise Exception("Failed to add Peer")

  def removePeer(self, _id, peer_id):
    if self.__handle.removePeer(_id.encode("utf-8"), peer_id.encode("utf-8")):
      raise Exception("Failed to remove Peer")