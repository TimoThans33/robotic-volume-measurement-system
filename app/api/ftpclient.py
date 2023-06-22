from ftplib import FTP, error_perm
from datetime import datetime, timedelta
import os
import asyncio
import concurrent.futures
import time
import threading

"""
FTP client class for handling ftp connections and file transfers.
    - login_() : sets the ftp credentials
    - login() : sets the ftp credentials from environment variables
    - connect(ip) : connects to the ftp server
    - close() : closes the ftp connection
    - list_all() : lists all files and directories in the ftp server
    - move_file(file) : moves a file to a new directory based on the file name
    - move_files_directly() : moves all files in the ftp server to a new directory based on the file name

The FTP client uses a big mutex lock to avoid race conditions between threads. The lock is released when the ftp connection is closed.
"""
class FTPclient():
    def __init__(self):
        self.ip = None
        self.ftp_instance = None
        self.ftp_user = None
        self.ftp_pass = None
        self.mutex = threading.Lock()
        self.loop = asyncio.get_event_loop()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.allowed_types = ["csv", "blob"]

    def login_(self, user, passw):
        self.ftp_user = user
        self.ftp_pass = passw
    
    def login(self):
        try:
            self.ftp_user = os.environ['FTP_USER']
            self.ftp_pass = os.environ['FTP_PASS']
        except KeyError:
            print("FTP credentials not set try: export FTP_USER=<user> FTP_PASS=<pass>")
            return

    def connect(self, ip):
        self.ip = ip
        if self.ftp_user is None or self.ftp_pass is None:
            print("FTP credentials not set")
            return

        """Big FTP client lock"""        
        self.mutex.acquire()
        self.ftp_instance = FTP(ip, user=self.ftp_user, passwd=self.ftp_pass)
    
    def close(self):
        """Big FTP client lock"""
        try:
            self.ftp_instance.close()
            self.ftp_instance = None
        finally:
            self.mutex.release()

    def list_all(self):
        print("listing files and directories in ftp://{} : {}".format(self.ip, self.ftp_instance.retrlines('LIST')))

    def move_file(self, file):
        if not file.endswith(".jpg"):
            if not file.endswith(".xml"):
                if not file.endswith(".pcd"):
                    #print("[ERROR] {} not a valid file".format(file), flush=True)
                    return
            
        file_name = file.split("/")[-1]
        date = file_name.split("_")[1:3]
        date = datetime.strptime("".join(date), "%Y%m%d%H%M%S")

        piece_id = file_name.split("_")[-1]
        piece_id = piece_id.split(".")[0]

        new_dir = date.strftime('%Y/%m/%d/%H%M%S/')
        
        store_dir = self.ftp_instance.pwd()
        self.ftp_instance.cwd("/")
        try:
            self.ftp_instance.rename(file_name, new_dir+file_name)
        except error_perm:
            self.chdir(new_dir)
            self.ftp_instance.rename(file_name, new_dir+file_name)
            self.ftp_instance.cwd(store_dir)
        return new_dir+file_name

    def move_files_directly(self):
        start_time = time.time()
        lines = []
        self.ftp_instance.dir("/", lines.append)
        for line in lines:
            file_name = line.split(" ")[-1]
            if line.startswith("d"):
                continue
            if not line.endswith(".jpg"):
                if not line.endswith(".xml"):
                    if not line.endswith(".pcd"):
                        print("deleting file {}".format(file_name))
                        self.ftp_instance.delete(file_name)
            
            date = file_name.split("_")[1:3]
            date = datetime.strptime("".join(date), "%Y%m%d%H%M%S")

            piece_id = file_name.split("_")[-1]
            piece_id = piece_id.split(".")[0]
            
            new_dir = date.strftime('%Y/%m/%d/%H%M%S/')

            store_dir = self.ftp_instance.pwd()
            self.ftp_instance.cwd("/")
            try:
                self.ftp_instance.rename(file_name, new_dir+file_name)
            except error_perm:
                self.chdir(new_dir)
                self.ftp_instance.rename(file_name, new_dir+file_name)
                self.ftp_instance.cwd(store_dir)
        print("finished moving files in {}s".format(time.time()-start_time), flush=True)

    def chdir(self, dir):
        try:
            saved_dir = self.ftp_instance.pwd()
            self.ftp_instance.cwd(dir)
        except error_perm:
            dir_arr = dir.split("/")
            for dir in dir_arr:
                try:
                    self.ftp_instance.cwd(dir)
                except error_perm:
                    self.ftp_instance.mkd(dir)
                    self.ftp_instance.cwd(dir)
        self.ftp_instance.cwd(saved_dir)


    def monitor_files(self, timer):        
        start = datetime.now()
        ls_prev = set()
        dir = "/"
        #print("monitoring files in ftp://{}{} at {}".format(self.ip, dir, start))
        while datetime.now() - start < timer:
            ls = set(self.ftp_instance.nlst(dir))
            add = ls-ls_prev
            if add: yield add
            ls_prev = ls  
            time.sleep(0.5)
        #print("finished monitoring files in ftp://{}/{} at {}".format(self.ip, dir, datetime.now()))

    def list_files(self, directory):
        if not self.ftp_instance:
            print("[ERROR] ftp not connected")
            return
        self.ftp_instance.cwd(directory)
        print("listing files and directories in ftp://{} : {}".format(self.ip, self.ftp_instance.retrlines('LIST')))
    
    def write(self, bytes_data):
        current_dir = self.ftp_instance.pwd()

        date = datetime.now()
        datestr = date.strftime("%Y-%m-%d %H:%M:%S")
        folder_str = date.strftime("%Y/%m/%d")
        
        try:
            self.ftp_instance.cwd("csv/{}".format(folder_str))
        except error_perm:
            print("directory does not yet exist, creating directory {}".format(folder_str))
            self.chdir("csv/{}".format(folder_str))
            self.ftp_instance.cwd("csv/{}".format(folder_str))

        self.ftp_instance.storbinary('STOR {}.csv'.format(datestr), bytes_data)
        self.ftp_instance.cwd(current_dir)