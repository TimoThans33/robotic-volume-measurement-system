#!/bin/bash

set -e

exec python3 ../main.py --namespace pv --partition dimensioner --port 5010 --ip 0.0.0.0 -c config.yaml --debug True &
exec python3 simulator.py -i 0.0.0.0 -p 5556 
