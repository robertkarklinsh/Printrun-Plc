import time
import os
import sys
import timeit
import cProfile
from utils import PlcError
from multiprocessing.pool import ThreadPool
from multiprocessing import Process, Pipe
from multiprocessing.queues import Queue
from threading import Thread, Timer, current_thread
from gcoder import LightGCode
from collections import defaultdict

TIME_OUT = 0.5

# pipe = Pipe()
# proc = Process(target=func, args=(pipe[1],))
# proc.start()
# for _ in xrange(10):
#     time.sleep(0.25)
#     while pipe[0].poll():
#         print pipe[0].recv()
#     else:
#         time.sleep(TIME_OUT)
# proc.terminate()
# proc.join()

gcode = LightGCode(deferred=True)   
gcode.prepare(open('apparat_plus_fast.gcode', 'r'), None, None)

