from tjess.transport.interface import Interface
from tjess.transport.peer import Peer
from tjess.transport.enums import Scope, MessageType, Status


class Node:
  def __init__(self, partition, name, libpath="/usr/local/lib/tjess/libtjess-transport-dll.so"):
    self.__partition = partition
    self.__name = name
    self.__id = "{}_{}".format(partition, name)
    self.__handle = Interface(libpath)
    self.__handle.createNode(partition, name)

  def close(self):
    self.__handle.closeNode(self.__id)

  def getId(self, id):
    return self.__handle.getId(self.__id)

  def getPartition(self):
    return self.__handle.getPartition(self.__id)

  def getName(self):
    return self.__handle.getName(self.__id)

  def getPort(self):
    return self.__handle.getPort(self.__id)

  def setPort(self, port):
    self.__handle.setPort(self.__id, port )

  def getIp(self):
    return self.__handle.getIp(self.__id)

  def setIp(self, ip):
    self.__handle.setIp(self.__id, ip)

  def getScope(self):
    return self.__handle.getScope(self.__id)

  def setScope(self, scope):
    self.__handle.setScope(self.__id, scope )

  def spinOnce(self):
    self.__handle.spinOnce(self.__id)

  def publish(self, scope, topic, msg):
    self.__handle.publish(self.__id, scope, topic, msg)

  def request(self, scope, peer_id,  remote_function_name, request, response_function_name=""):
    self.__handle.request(self.__id, scope, peer_id, remote_function_name, request, response_function_name)

  def remoteFunction(self, scope, command, func):
    self.__handle.remoteFunction(self.__id,scope, command, func)     
     
  def responseFunction(self, scope, command, func):
    self.__handle.responseFunction(self.__id,scope, command, func) 

  def subscribe(self, scope, topic, func):
    self.__handle.subscribe(self.__id, scope, topic, func)



  def addPeer(self, peer: Peer):
    self.__handle.createPeer(peer.partition, peer.name, peer.ip, peer.port)
    self.__handle.addPeer(self.__id, peer.id)
  
  def removePeer(self, peer: Peer):
    self.__handle.removePeer(self._id, peer.id)