#!/usr/bin/python3
import asyncio
from datetime import datetime
import time
import concurrent.futures
import schedule

class Dimensioner():
    def __init__(self):
        self.loop = asyncio.get_event_loop()     
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.schedulers = ['weekly','daily', 'hourly', '30sec', '10sec']
        self.SICK = None
        self.qb_websocket = None
        self.peers = None
        self.mdbserver = None
        self.tjess_node = None
        self.api = None
        self.wt = None
        self.HTTPserver = None
                
        self.timed_coroutines = []
        self.scheduled_coroutines = []

    def add_timed_coroutine(self, hour, coroutine):
        self.timed_coroutines.append((hour, coroutine))

    def ceil_dt(self, dt, delta):
        return dt + (datetime.min - dt) % delta
    
    def add_scheduled_coroutine(self, start, interval, coroutine):
        if len(self.scheduled_coroutines) < 4:
            if interval not in self.schedulers:
                print("invalid scheduler", flush=True)
                return
            else:
                if interval == 'weekly':
                    print("starting coroutine {} weekly on monday at {}".format(coroutine.__name__, start.strftime("%H:%M:%S")), flush=True)
                    schedule.every().monday.at(start.strftime("%H:%M:%S")).do(coroutine)
                if interval == 'daily':
                    print("starting coroutine {} daily at {}".format(coroutine.__name__, start.strftime("%H:%M:%S")), flush=True)
                    schedule.every().day.at(start.strftime("%H:%M:%S")).do(coroutine)
                elif interval == 'hourly':
                    print("starting coroutine {} hourly at {}".format(coroutine.__name__, start.strftime("%M:%S")), flush=True)
                    schedule.every().hour.at(start.strftime("%M:%S")).do(coroutine) 
                elif interval == '30sec':
                    print("starting coroutine {} every 30 seconds".format(coroutine.__name__), flush=True)
                    schedule.every(30).seconds.do(coroutine)
                elif interval == '10sec':
                    print("starting coroutine {} every 10 seconds".format(coroutine.__name__), flush=True)
                    schedule.every(10).seconds.do(coroutine)
        else:
            print("too many scheduled coroutines", flush=True)

    def run_scheduled_coroutines_(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
         
    def run_scheduled_coroutines(self):
        self.loop.run_in_executor(self.executor, self.run_scheduled_coroutines_)
    
    def run_timed_coroutines(self):
        for timer, coroutine in self.timed_coroutines:
            self.loop.create_task(self.timed_coroutine_loop(timer, coroutine))    
    
    def scheduled_coroutine_loop(self, starting_time, interval, coroutine, scheduler):
        print("scheduled coroutine: {} started at {}".format(coroutine.__name__, starting_time.strftime("%H:%M:%S")), flush=True)
        scheduler.run()
        print("scheduled coroutine: {} finished at {}".format(coroutine.__name__, datetime.now().strftime("%H:%M:%S")), flush=True)
        dt = starting_time + interval
        scheduler.enter(dt.timestamp(), 1, coroutine)

    async def timed_coroutine_loop(self, timer, coroutine):
        #print("starting timed coroutine: {}".format(coroutine.__name__))
        while True:
            await coroutine()
            await asyncio.sleep(timer.total_seconds())
    
    def run(self):
        self.run_timed_coroutines()
        self.run_scheduled_coroutines()
        self.loop.run_forever()