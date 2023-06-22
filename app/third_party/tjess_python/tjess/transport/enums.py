from enum import Enum, IntEnum

class MessageType(IntEnum):
  DEFAULT=0
  REQUEST_REPLY=1
  REQUEST_ONLY=2
  RESPONSE=3

class Scope(IntEnum):
  PROCESS=0
  HOST=1
  PARTITION=2
  GLOBAL=3


class Status(IntEnum):
  DISCONNECTED=0
  CONNECTED=1
  EVASIVE=2
  EXPIRED=3