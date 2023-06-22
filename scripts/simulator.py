import asyncio
import websockets
import random
import json
import sys
from ftplib import FTP, error_perm
from datetime import datetime, timedelta
import glob, os
import concurrent.futures

"""
front-end websocket server
"""
class qb_websocket_server():
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.ws = None
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.serve())
        self.CLIENTS = set()

    async def serve(self):
        websocket = await websockets.serve(self.ws_handler, self.ip, self.port)
        self.ws = websocket
        print("serve qb websocket on {}:{}".format(self.ip, self.port))
        await websocket.wait_closed()

    async def ws_handler(self, websocket, path):
        self.CLIENTS.add(websocket)
        async for msg in websocket:
            for ws in self.CLIENTS.copy():
                try:
                    await ws.send(msg)
                except websockets.ConnectionClosed:
                    self.CLIENTS.remove(ws)
                    print("client disconnected")
"""
front-end websocket client
"""
class qb_websocket_client():
    def __init__(self, ip, port, callback):
        self.ip = ip
        self.port = port
        self.ws = None
        self.read_callback = callback
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.connect())
    
    async def connect(self):
        await asyncio.sleep(3)
        async with websockets.connect("ws://{}:{}/ws".format(self.ip, self.port)) as websocket:
            if websocket.open:
                print("connected to qb websocket on {}:{}".format(self.ip, self.port))
                self.ws = websocket
                await self.ws_handler(websocket)
            else:
                print("failed to connect to qb websocket on {}:{}".format(self.ip, self.port))
                await asyncio.sleep(1)
                self.loop.create_task(self.connect())

    def ws_writer(self, msg):
        self.loop.create_task(self.ws_writer_(msg))

    async def ws_writer_(self, msg):
        if self.ws:
            await self.ws.send(msg)
        else:
            print("no qb websocket connection")

    async def ws_handler(self, websocket):
        async for msg in websocket:
            self.loop.create_task(self.read_callback(msg))

class FTPclient():
    def __init__(self):
        self.ip = None
        self.ftp_instance = None
        self.loop = asyncio.get_event_loop()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    
    def connect(self, id, type, ip):
        self.loop.run_in_executor(self.executor, self.connect_, id, type, ip)

    def connect_(self, id, type, ip):
        self.ip = ip
        self.ftp_instance = FTP(ip, user=os.environ['FTP_USER'], passwd=os.environ['FTP_PASS'])
        print("connected to ftp server {}".format(ip))
        self.ftp_instance.cwd("/")
    
    def write(self):
        self.loop.run_in_executor(self.executor, self.write_)
    
    def write_(self):
        #print("writing to ftp server {} at {}".format(self.ip, datetime.now().strftime("%Y%m%d_%H%M%S"))) 
        root_name = "AMR_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.chdir("./")
        jpg_files = glob.glob("*.jpg")
        xml_files = {}
        pcd_files = {}
        for jpg in jpg_files:
            xml_files[jpg[:-4]] = glob.glob("{}*.xml".format(jpg[:-4]))
            pcd_files[jpg[:-4]] = glob.glob("{}*.pcd".format(jpg[:-4]))
        for jpg in jpg_files:
            name = root_name + "_0000{:06d}".format(random.randint(1, 100000))
            with open(jpg, "rb") as f:
                self.ftp_instance.storbinary("STOR {}".format(name+".jpg"), f)
            f.close()
            for xml in xml_files[jpg[:-4]]:
                with open(xml, "rb") as f:
                    self.ftp_instance.storbinary("STOR {}".format(name+".xml"), f)
            f.close()
            for pcd in pcd_files[jpg[:-4]]:
                with open(pcd, "rb") as f:
                    self.ftp_instance.storbinary("STOR {}".format(name+".pcd"), f)
            f.close()

class tcpconnector():
    def __init__(self, host, port):
        self.loop = asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.loop.create_task(self.connect())
        self.reader = None
        self.writer = None
    
    async def connect(self):
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                self.reader = reader
                self.writer = writer
                print("connected to {}:{}".format(self.host, self.port))
                break
            except Exception as e:
                print(e)
                await asyncio.sleep(1)
                continue
    
    async def send(self, msg):
        if self.writer:
            self.writer.write(msg)
            await self.writer.drain()
        else:
            print("no tcp connection")

class application():
    def __init__(self, ip, dev=False):
        # websocket echo server
        self.qbws_server = qb_websocket_server("0.0.0.0", 5556)
        # websocket client
        self.qbws = qb_websocket_client("0.0.0.0", 5556, self.qbws_callback)
        # store the loop
        self.loop = asyncio.get_event_loop()
        # tcp connector
        self.tcp_connector = tcpconnector("127.0.1.1", 2001)
        # ftp client
        self.ftp_client = FTPclient()
        self.ftp_client.connect("id", "blob", "localhost")
        # activate message loop
        self.gen_msg()

    def gen_msg(self):
        self.loop.create_task(self.gen_msg_())
    
    async def gen_msg_(self):
        while self.qbws.ws is None:
            await asyncio.sleep(1)
        
        barcode_init = "4206005698049202090135079104324001"
        direction = random.randint(1, 120)
        piece_id = barcode_init[:-2] + "{:02d}".format(random.randint(1, 15))
        robot_id = "{:04d}".format(random.randint(1000, 2000))
        
        self.qbws.ws_writer(self.piece_to_output(piece_id, direction, robot_id))
        await asyncio.sleep(1)
        chance = random.randint(1, 3)
        if chance == 1:
            print("[1] simulator: piece_id: {}, direction: {}, robot_id: {}".format(piece_id, direction, robot_id))
            await self.tcp_connector.send(self.piece_at_tunnel(robot_id=robot_id, barcode=piece_id))
            await asyncio.sleep(0.1)
            self.ftp_client.write()
            await self.tcp_connector.send(self.piece_at_tunnel())
        if chance == 2:
            print("[2] simulator: piece_id: {}, direction: {}, robot_id: {}".format(piece_id, direction, robot_id))
            await self.tcp_connector.send(self.piece_at_tunnel())
            await asyncio.sleep(0.1)
            await self.tcp_connector.send(self.piece_at_tunnel(robot_id=robot_id, barcode=piece_id))
            await asyncio.sleep(0.1)
            self.ftp_client.write()
        if chance == 3:
            print("[3] simulator: piece_id: {}, direction: {}, robot_id: {}".format(piece_id, direction, robot_id))
            await self.tcp_connector.send(self.piece_at_tunnel(robot_id=robot_id, barcode=piece_id))
            await asyncio.sleep(0.1)
            self.ftp_client.write()
            await asyncio.sleep(0.1)
        await asyncio.sleep(1)
        self.qbws.ws_writer(self.piece_at_dropoff(piece_id, direction, robot_id))
        await asyncio.sleep(5)
        self.gen_msg()


    def piece_at_dropoff(self, piece_id, direction, robot_id):
        weight = random.randint(1, 1000)/1000
        return json.dumps({"description":{"problem":"","solution":"","title":"Send Piece"},"topic":"/qb/ds/piece_at_output","value":{"barcode":piece_id,"direction":direction,"robot":robot_id, "weight":weight}})

    def piece_at_tunnel(self, robot_id="", barcode=None):
        if barcode:
            barcode_msg = ""
            pick_id_on = random.randint(0,2)
            for count in range(random.randint(0,4)):
                if count==pick_id_on:
                    barcode = barcode
                else:
                    barcode = "2700000"
                barcode_msg += "<Barcode Type=\"CODE128\" Length=\"24\" Coding=\"ASCII\" Data=\"{}\" TotalScans=\"5\" BestDevice=\"1\"><AbsolutePosition X=\"0\" Y=\"0\" Z=\"0\"/><RelativePosition XR=\"3000\" YR=\"0\" ZR=\"0\"/><ReadList><Device ID=\"1\" Scans=\"5\"/></ReadList></Barcode>".format(barcode)
            barcode_msg += "<Barcode Type=\"DATAMATRIX\" Length=\"11\" Coding=\"ASCII\" Data=\"r007c11{}\" TotalScans=\"0\" BestDevice=\"1\"><AbsolutePosition X=\"0\" Y=\"0\" Z=\"0\"/><RelativePosition XR=\"3000\" YR=\"0\" ZR=\"0\"/><ReadList><Device ID=\"1\" Scans=\"2\"/></ReadList></Barcode>""".format(robot_id)
            message = "<MSG Type=\"BarcodesProcessed\"><Protocol Version=\"003\"/><Sender UnitNr=\"00000001\"/><Index ID=\"0000000009\" ID2=\"0000000000\" ID3=\"0000000000\" /><BarcodeList>{}</BarcodeList></MSG>".format(barcode_msg) 
        else:
            dist = random.randint(0,5)
            if dist == 1:
                Reliability = "ERROR"
                length = str(0)
                width = str(0)
                height = str(0)
                vol = float(length) * float(width) * float(height)
            else:
                Reliability = "OK"
                length = str(random.randint(100, 200)/100)
                width = str(random.randint(100, 200)/100)
                height = str(random.randint(100, 200)/100)
                vol = float(length) * float(width) * float(height)
            
            message = "<MSG Type=\"DimensionReceived\"><Protocol Version=\"003\"/><Sender UnitNr=\"1010\"/><Index ID=\"0000003201\" ID2=\"0000000000\" ID3=\"0000000000\"/><Properties Shadowing=\"1\" ObjectGap=\"1754\" OGAUnit=\"1\" ObjectTriggerLength=\"256\" OTLUnit=\"1\" ObjectSpeedTrigger=\"1180\" OSTUnit=\"1\"/><Volume AlibiID=\"0000000020230208170959785\" Reliability=\"{}\" MeasurementStatus=\"0\" MeasurementStatus2=\"0\" MeasurementStatus3=\"1\" MeasurementStatus4=\"0\" Length=\"{}\" Width=\"{}\" Height=\"{}\" DistanceUnit=\"1\" BoxVolume=\"{}\" RealVolume=\"10680\" VolumeUnit=\"1\" Source=\"33\"/><Scale Status=\"0\" Weight=\"0\" ScaleUnit=\"0\"/><LFT Status=\"U\"/></MSG>".format(
                            Reliability, length, width, height, vol)
            
        return message.encode()

    def piece_to_output(self, piece_id, direction, robot_id):
        return json.dumps({"description":{"problem":"","solution":"","title":"Send Piece"},"topic":"/qb/ds/piece_to_output","value":{"barcode":piece_id,"direction":direction,"robot":robot_id}})
        
    async def qbws_callback(self, msg):
        pass

    def run(self):
        self.loop.run_forever()


if __name__ == "__main__":
    app = application("0.0.0.0")
    app.run()