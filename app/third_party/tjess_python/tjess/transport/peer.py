from tjess.transport.enums import Scope, Status



class Peer(object):
  def __init__(self, partition, name, ip, port):
    self.partition = partition
    self.name = name
    self.id = "{}_{}".format(partition, name)
    self.ip = str(ip)
    self.port = int(port)
    self.scope = Scope.HOST
    self.status = Status.DISCONNECTED