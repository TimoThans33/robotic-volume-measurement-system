# tjess-python

python bindings for tjess libraries. Tjess Transport is a simple ZeroMQ wrapper that implements asynchronous request reply pattern and a publisher subscriber pattern.

## Install
You must have the tjess-transport package installed on your system. The latest working version is added to this repository.
```
python3 setup.py install
```

## Usage
The library consists of the following.
```
├── decorators.py # for creating callback functions
├── enums.py
├── interface.py # C++ wrapper do not use directly
├── peer.py # tjess peers objects
└── node.py # user library
```
