#!/usr/bin/python3
from app.dimensioner import Dimensioner
from app.dimensioner import coroutines
from app.api.ftpclient import FTPclient

application = Dimensioner()
application.SICK = coroutines.SICK_()
application.FTPclient = FTPclient()
