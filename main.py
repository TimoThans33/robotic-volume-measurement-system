#!/usr/bin/python3
from app import application
from app.api.websockets import QBWebsocket
from app.api.tcpconnectors import XMLconnector, TJESSconnector, TJESSpeer
from app.api.httpserver import HTTPserver
from datetime import timedelta, datetime
import argparse
import yaml


parser = argparse.ArgumentParser(description='pvt dimensioner client')
### REQUIRED ###
parser.add_argument('--ip', type=str, default="0.0.0.0",
                    help='ip address of the server')
parser.add_argument('--port', type=int, default="8080",
                    help='port of the server')
### OPTIONAL ###
parser.add_argument('--partition','-p', type=str, default="pv",
                    help='partition of the server')
parser.add_argument('--namespace','-n', type=str, default="dimensioner",
                    help='namespace of the server')
parser.add_argument('--config', '-c', type=str, default="pvt-dimensioner-client.yaml",
                    help='config file of the server')   
parser.add_argument('--debug', type=bool, default=False,
                    help='debug mode')
args = parser.parse_args()

with open(args.config, 'r') as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

def main():
###### CONFIGURATIONS ######
    application.SICK.connect_mdb(config["mongod_connection_string"])
    application.SICK.ftp_ip = config["ftp_ip"]   

    interval = config["csv_writer_interval"]
    if "csv_writer_starting_time" in config.keys():
        if config["csv_writer_starting_time"] == "now":
            starting_time = datetime.now() + timedelta(seconds=30)
        else:
            starting_time = config["csv_writer_starting_time"]
    else:
        today = datetime.now()
        starting_time = datetime(today.year, today.month, today.day, 0, 0, 0)

    if "ftp_user" and "ftp_password" in config.keys():
        application.SICK.FTP.login_(config["ftp_user"], config["ftp_password"])
    else:
        application.SICK.FTP.login()
    
    if "print_raw_xml" in config.keys():
        application.tcpconnector = XMLconnector(config["sick_ip"], config["sick_port"], print_raw_xml=config["print_raw_xml"])
    else:
        application.tcpconnector = XMLconnector(config["sick_ip"], config["sick_port"])
    
    if "print_sick_callbacks" in config.keys():
        application.SICK.print_callback = config["print_sick_callbacks"]
###########################

###### DEBUG MODE ######
    if args.debug:
        print("debug mode")
        application.qb_websocket = QBWebsocket(config["qb_ip"], config["qb_port"])
        application.qb_websocket.add_subscriber("/qb/ds/piece_to_output", application.SICK.payload_callback)
        application.qb_websocket.add_subscriber("/qb/ds/piece_at_output", application.SICK.dropoff_callback)
#########################

###### ADD ALL COROUTINES #######
    application.SICK.mdb.add_subscriber("dropoffs", "piece_at_output", application.SICK.piece_at_output_callback)
    
    application.SICK.clear_ftp()
    application.add_scheduled_coroutine(starting_time, interval, application.SICK.clear_ftp)
    application.add_scheduled_coroutine(starting_time, interval, application.SICK.csv_writer)
    
    if not args.debug:
        for peer in config["peers"]:
            tjess_peers = [TJESSpeer(peer["partition"], peer["id"], peer["ip"], peer["port"])]
            application.tjess_node = TJESSconnector(args.partition, args.namespace, args.port, tjess_peers)
            application.SICK.tjess_node = application.tjess_node
    
    application.tcpconnector.add_subscriber("BarcodesProcessed", application.SICK.barcode_callback)
    application.tcpconnector.add_subscriber("DimensionReceived", application.SICK.dimension_callback)
    application.tcpconnector.add_subscriber("StatusRequest", application.SICK.heartbeat)
##################################

####### HTTP SERVER ###########
    application.HTTPserver = HTTPserver(config["http_ip"], config["http_port"], config["mongod_connection_string"])
    application.run()
################################

if __name__ == '__main__':
    main()
