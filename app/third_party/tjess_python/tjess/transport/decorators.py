from inspect import signature
from ctypes import *
# Decorators, for use with callbacks
def request_callback(func):
    def wrapper(req, meta):
      sig_len = len(signature(func).parameters)
      if sig_len == 2:
        rep = func(cast(req, c_char_p).value.decode(), cast(meta, c_char_p).value.decode())
      elif sig_len == 1:
        rep = func(cast(req, c_char_p).value.decode())
      return rep
    return wrapper

def response_callback(func):
    def wrapper(req):
      func(cast(req, c_char_p).value.decode())
    return wrapper

def subscribe_callback(func):
    def wrapper(req):
      func(cast(req, c_char_p).value.decode())
    return wrapper

def request_callback_method(obj):
  def request_callback_inner(func):
    def wrapper(req, meta):
      sig_len = len(signature(func).parameters)
      if sig_len == 3:
        rep = func(obj,cast(req, c_char_p).value.decode(), cast(meta, c_char_p).value.decode())
      elif sig_len == 2:
        rep = func(obj,cast(req, c_char_p).value.decode())
      return rep
    return wrapper
  return request_callback_inner

def subscribe_callback_method(obj):
  def subscribe_callback_inner(func):
    def wrapper(req):
      func(obj,cast(req, c_char_p).value.decode())
    return wrapper
  return subscribe_callback_inner