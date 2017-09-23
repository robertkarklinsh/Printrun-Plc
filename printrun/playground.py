from gcoder import LightGCode
import serial
from plc.plc_handler import set_for_callback
import time
import multiprocessing

# -----------------------------------------------
# Real object size
# ------------------------------------------------
# from __future__ import print_function
# import cPickle
# from gcoder import LightGCode
# from sys import getsizeof, stderr
# from itertools import chain
# from collections import deque
# from array import array
#
# try:
#     from reprlib import repr
# except ImportError:
#     pass
#
#
# def total_size(o, handlers={}, verbose=False):
#     """ Returns the approximate memory footprint an object and all of its contents.
#
#     Automatically finds the contents of the following builtin containers and
#     their subclasses:  tuple, list, deque, dict, set and frozenset.
#     To search other containers, add handlers to iterate over their contents:
#
#         handlers = {SomeContainerClass: iter,
#                     OtherContainerClass: OtherContainerClass.get_elements}
#
#     """
#     dict_handler = lambda d: chain.from_iterable(d.items())
#     all_handlers = {tuple: iter,
#                     list: iter,
#                     array: iter,
#                     deque: iter,
#                     dict: dict_handler,
#                     set: iter,
#                     frozenset: iter,
#                     }
#     all_handlers.update(handlers)  # user handlers take precedence
#     seen = set()  # track which object id's have already been seen
#     default_size = getsizeof(0)  # estimate sizeof object without __sizeof__
#
#     def sizeof(o):
#         if id(o) in seen:  # do not double count the same object
#             return 0
#         seen.add(id(o))
#         s = getsizeof(o, default_size)
#
#         if verbose:
#             print(s, type(o), repr(o), file=stderr)
#
#         for typ, handler in all_handlers.items():
#             if isinstance(o, typ):
#                 s += sum(map(sizeof, handler(o)))
#                 break
#         return s
#
#     return sizeof(o)


##### Example call #####

# if __name__ == '__main__':
#     d = dict(a=1, b=2, c=3, d=[4,5,6,7], e='a string of chars')
#     print(total_size(d, verbose=True))

TIME_OUT = 1


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

s = serial.Serial()
print "OK"
# gcode = LightGCode(deferred=True)
# gcode.prepare(open('pu700_body1.gcode', 'r'), None, None)

# dict = str(gcode.__dict__)
# with open('apparatus_super_fast.txt', 'w') as output:
#     output.write(dict)
#
# print (total_size(gcode.__dict__, verbose=False))
#
# with open('apparat_plus_fast.pkl', 'wb') as output:
#     cPickle.dump(gcode, output)
#
# with open('apparat_plus_fast.pkl', 'rb') as input:
#     new_gcode = cPickle.load(input)
# print new_gcode.__dict__

#
# class foo(multiprocessing.Process):
#     def run(self):
#         self.dummy_func('msg')
#         time.sleep(0.5)
#         self.dummy_func('msg')
#         time.sleep(0.5)
#         self.dummy_func('msg')
#         time.sleep(0.5)
#         self.dummy_func('msg')
#         time.sleep(4)
#
#     def dummy_func(self, msg=None, *args, **kwargs):
#         self.dummy_func = set_for_callback(self, TIME_OUT, msg)(self.dummy_func)
#         # if msg is None:
#         #     print "Function called for first time"
#         # else:
#         print "Function called"
#
#     def on_error(self, *args):
#         print "Time finished:("
#
#
# var = foo()
# var.start()
# var.join()


# var = foo()
# var.dummy_func()
# time.sleep(0.5)
# var.dummy_func('msg')
# time.sleep(1)
