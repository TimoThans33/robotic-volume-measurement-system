import json
import asyncio
import time
from app.mongodb import MDBclient
from app.dimensioner import Dimensioner
from app.api.ftpclient import FTPclient
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import io
import pandas
from app.util import sick_img_file_decode

"""
    This class is includes all the coroutines for the SICK dimensioner. These functions can be used to run the SICK dimensioner in a non-blocking way:
        - barcode reader:
            - can be used with Prime Visions XML connector
            - reads the barcode from the SICK dimensioner with Prime Visions XML connector
            - adds the barcode to the barcode queue
            - stores the barcode in the mongodb server
        - dimension reader:
            - can be used with Prime Visions XML connector
            - Must be used with the barcode reader
            - reads the dimensions from the SICK dimensioner with Prime Visions XML connector
            - pulls the barcode from the barcode queue and links it to the dimensions
            - stores the dimensions in the mongodb server
            - sends the dimensions with the TJESS connector
        - output reader:
            - can be used with the mongodb poller
            - reads the dropoff data from the mongodb server
            - matches the dropoff data with the dimensions
        - csv writer
            - dumps data from the mongodb server to a csv file
        - clear FTP
            - clears the root folder of the ftp server
            - creates the blob store folder
        - heartbeat
            - sends a heartbeat to the TJESS connector

    In simulation the websocket coroutines can be used to fill the mongodb server with data:
        - payload callback
            - reads the payload from the websocket
            - adds the payload to to the mongodb server
        - dropoff callback
            - reads the dropoff from the websocket
            - adds the dropoff to to the mongodb server
"""
class SICK_():
    def __init__(self):
        self.barcodequeue = asyncio.Queue()
        self.dimensionqueue = asyncio.Queue()

        self.ftpqueue = asyncio.Queue()
        self.tjess_node = None
        self.mdb = None
        self.FTP = FTPclient()
        self.ftp_ip = None
        self.dimensioner_id = None
        self.print_callback = False

    def connect_mdb(self, connection_string): 
        self.mdb = MDBclient(connection_string)

    def clear_ftp(self):
            if not self.ftp_ip:
                print("no ftp ip set", flush=True)
                return
            self.FTP.connect(self.ftp_ip)
            self.FTP.move_files_directly()
            self.FTP.close()

    def csv_writer(self):
        print("running scheduled csv writer at ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), flush=True)
        if not self.ftp_ip:
            print("no ftp ip set", flush=True)
            return
        if not self.mdb.is_connected:
            print("database disconnected unable to write csv", flush=True)
            return
        
        collection = self.mdb.get_collection("sorting-data", "payload")
        dimensioned_items = collection.find({
            "time": {"$gt": datetime.timestamp(datetime.now()-timedelta(hours=24))},
        })

        df = pandas.DataFrame(list(dimensioned_items))
        if not df.empty:
            df = df.drop(columns=["_id"])
        bytes_data = io.BytesIO( df.to_csv(index=False).encode() )

        self.FTP.connect(self.ftp_ip)
        self.FTP.write(bytes_data)
        self.FTP.close()
        
    async def barcode_callback(self, data):
        if not self.mdb.is_connected:
            print("database disconnected unable to write barcodes", flush=True)
            return
        collection = self.mdb.get_collection("sorting-data", "payload")
        
        root = ET.fromstring(data)
        for child in root:
            barcodes = []
            if child.tag == "BarcodeList":
                for barcode in child:
                    barcodes.append({"type": barcode.attrib["Type"], "barcode": barcode.attrib["Data"]})
        if self.print_callback:
            print("barcode callback : ", barcodes, flush=True)
        self.barcodequeue.put_nowait(barcodes)

        # clear barcode queue after 1 second if no dimension recieved
        dimension_status = "OK"
        counter = 0
        while self.dimensionqueue.empty():
            await asyncio.sleep(0.01)
            if counter > 10:
                print("[ERROR] timeout on barcode message, clearing barcode queue")
                dimension_status = "TIMEOUT"
                while not self.barcodequeue.empty():
                    self.barcodequeue.get_nowait()
                    self.barcodequeue.task_done()
                break
            counter += 1
        
        while not self.dimensionqueue.empty():
            self.dimensionqueue.get_nowait()
        
        if not self.ftp_ip:
            print("no ftp ip set", flush=True)
            return
        self.FTP.connect(self.ftp_ip)

        files = []
        for file in self.FTP.monitor_files(timedelta(seconds=3)):
            file_str = ','.join('%s' % i for i in file)
            for i in file_str.split(","):
                name = i.split("/")[-1]
                if i.endswith(".xml") or i.endswith(".jpg") or i.endswith(".pcd"):
                    files.append(name)
        for i in files: 
            self.FTP.move_file(i)
        self.FTP.close()
        
        if dimension_status is not "TIMEOUT":
            self.ftpqueue.put_nowait(sick_img_file_decode(files[0]) if files else "")
                
        collection.insert_one({"type": "piece_at_lector",
            "barcodes": [list(barcode.values())[1] for barcode in barcodes],
            "dimension_status": dimension_status,
            "file_path": sick_img_file_decode(files[0]) if files else "",
            "time": datetime.timestamp(datetime.now())})
    
    async def piece_at_output_callback(self, doc):
        if not self.mdb.is_connected:   
            return
        collection = self.mdb.get_collection("sorting-data", "payload")

        if self.print_callback:
            print("piecematch callback : {}".format([{"barcode": doc["barcode"], "robot": doc["robot"]}]), flush=True)

        # piecematch algorithm: latest piece in dropoff data with same barcode in the past 24h
        volumetric_item = collection.find({
            "type": "piece_at_dimensioner",
            "barcode": doc["barcode"],
            "time": {"$gt": datetime.timestamp(datetime.fromtimestamp(doc["time"])-timedelta(hours=24))},
        }).sort("time", 1).limit(1)
        volumetric_item = list(volumetric_item)

        dimension_status = volumetric_item[0]["reliability"] if len(volumetric_item) > 0 else "NO_MATCH"   
        
        if len(volumetric_item) > 0:        
            for item in volumetric_item:
                collection.insert_one({"type": "piece_dimensioned",
                                    "time": datetime.timestamp(datetime.now()),
                                    "barcode": doc["barcode"],
                                    "robot": doc["robot"],
                                    "direction": doc["direction"],
                                    "weight": doc["weight"],
                                    "file_path": item["file_path"] if "file_path" in item else "",
                                    "volume": item["boxvolume"],
                                    "dimension_status": dimension_status,
                                    "dimensions": item["dimensions"]})
        else:
            print("[WARNING] no match found for piece with id {} from robot {}".format(doc["barcode"], doc["robot"]), flush=True)
            collection.insert_one({"type": "piece_dimensioned",
                    "time": datetime.timestamp(datetime.now()),
                    "barcode": doc["barcode"],
                    "robot": doc["robot"],
                    "direction": doc["direction"],
                    "weight": doc["weight"],
                    "volume": "",
                    "file_path": "",
                    "dimension_status": dimension_status,
                    "dimensions": {}})

    async def dimension_callback(self, data):
        if not self.mdb.is_connected:
            print("database disconnected unable to write dimensions", flush=True)
            return
        collection = self.mdb.get_collection("sorting-data", "payload")
        root = ET.fromstring(data)
        ddict = {}
        for dimension in root.findall("Volume"):
            ddict["length"] = dimension.attrib["Length"]
            ddict["width"] = dimension.attrib["Width"]
            ddict["height"] = dimension.attrib["Height"]
            boxvolume = dimension.attrib["BoxVolume"]
            reliability = dimension.attrib["Reliability"]

        self.dimensionqueue.put_nowait(ddict)

        now = datetime.now()
        counter = 0
        while self.barcodequeue.empty():
            await asyncio.sleep(0.01)
            if counter > 10:
                print("[ERROR] timeout on dimension message, clearing dimension queue", flush=True)
                while not self.dimensionqueue.empty():
                    self.dimensionqueue.get_nowait()
                    self.dimensionqueue.task_done()
                return
            counter+=1

        piece_id = self.barcodequeue.get_nowait()
        
        """ MATCHING ALGORITHM """
        matching_performance = datetime.now()
        robot_id = ""
        direction = ""
        items = []
        matched_barcode = ""
        for barcode in filter(lambda piece: piece["type"] == "DATAMATRIX", piece_id):
            # allow matches in past two minutes
            robot_id = barcode["barcode"][-4:]
            item = collection.find({"type": "piece_on_robot", 
                                    "robot": robot_id,
                                    "time": {"$gt": datetime.timestamp(datetime.now() - timedelta(minutes=2))}}).sort("_id",-1).limit(1)    
            item = list(item)
            if item:
                items.append(item[0])
                break
        if not items:
            for barcode in filter(lambda k: k == "CODE128", piece_id):
                # allow for past two minutes
                item = collection.find({"type": "piece_on_robot",
                                        "barcode": barcode["barcode"],
                                        "time": {"$gt": datetime.timestamp(datetime.now() - timedelta(minutes=2))}}).sort("_id",-1).limit(1)
                item = list(item)
                if item:
                    items.append(item[0])
                    break
        matching_performance = datetime.now() - matching_performance
        """ END MATCHING ALGORITHM """

        if len(items) > 0:
            items = items[0]
            if not robot_id:
                robot_id = items["robot"]
            direction = items["direction"]
            matched_barcode = items["piece_id"]

        else:
            print("[WARNING] no match found for piece with id {}".format(piece_id), flush=True)
        
        if self.print_callback:
            print("dimension callback : ", piece_id, robot_id, direction, boxvolume, ddict, flush=True)
        
        if self.tjess_node:
            self.tjess_node.sendrequest("qb_api", "publishToWebsocket",
                json.dumps({"topic": "/qb/ds/piece_in_tunnel",
                            "value": {"extra":
                            {"barcode": matched_barcode, 
                            "robot_id": robot_id,
                            "direction": direction,
                            "volume": boxvolume,
                            "reliability": reliability,
                            "dimensions": ddict}}}))
                
        counter = 0
        ftp_status = "OK"
        while self.ftpqueue.empty():
            counter += 1
            await asyncio.sleep(0.1)
            if counter > 30:
                print("[ERROR] ftp queue timeout", flush=True)
                ftp_status = "TIMEOUT"
                break
        
        if ftp_status == "OK":
            img_file = self.ftpqueue.get_nowait()
        else:
            img_file = ""
        
        collection.insert_one({"type": "piece_at_dimensioner",
                                "time": datetime.timestamp(datetime.now()), 
                                "barcode": matched_barcode,
                                "matching_performance": matching_performance.total_seconds(),
                                "ftp_status": ftp_status,
                                "file_path": img_file, 
                                "robot": robot_id,
                                "direction": direction,
                                "boxvolume": boxvolume,
                                "reliability": reliability,
                                "dimensions": ddict})


    async def heartbeat(self, data):
        if self.print_callback:
            print("heartbeat callback: ", data, flush=True)
        if self.tjess_node:
            self.tjess_node.sendrequest("qb_api", "publishToWebsocket",
                json.dumps({"topic": "/qb/ds/sickheartbeat",
                            "value": {"extra":
                                      {"status": "CONNECTED"}}}))
    
    async def dropoff_callback(self, data):
        if not self.mdb.is_connected:
            return
        collection = self.mdb.get_collection("sorting-data", "dropoffs")

        data_dict = json.loads(data)
        collection.insert_one({"type": "piece_at_output",
                                "time": datetime.timestamp(datetime.now()),
                                "robot": data_dict["value"]["robot"],
                                "direction": data_dict["value"]["direction"],
                                "barcode": data_dict["value"]["barcode"],
                                "weight": data_dict["value"]["weight"]})

    async def payload_callback(self, data):
        if not self.mdb.is_connected:
            print("database disconnected unable to write payload", flush=True)
            return
        collection = self.mdb.get_collection("sorting-data", "payload")

        data_dict = json.loads(data)
        collection.insert_one({
            "type": "piece_on_robot",
            "time": datetime.timestamp(datetime.now()),
            "piece_id": data_dict["value"]["barcode"],
            "robot": data_dict["value"]["robot"],
            "direction": data_dict["value"]["direction"],
        })