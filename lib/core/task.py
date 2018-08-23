#!/usr/bin/python 
# -*- coding: utf-8 -*-

import multiprocessing
import os

READY = 0
RUNNING = 1
COMPLETE = 2
STOP = 3

class Content:
	process_map = {}
	
	def __init__(self):
		pass
#process maping {task id:<Process(Process-x, xxxxx)>}




class Process(multiprocessing.Process):
	
	def stop(self):
		os.system('kill -9 %d'%self.pid)