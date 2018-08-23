#!/usr/bin/python 
# -*- coding: utf-8 -*-

import json
import datetime
from multiprocessing import Process
from flask_classful import FlaskView, route
from nameko.web.handlers import http
from needlebox.bruteforce import WebPathBrute
import psutil

from lib.core.database import Wordlist, Database
from lib.core.task import Process

import time
import os
class ApiService():

	def __init__(self, key):
		self._db = Database(key)
		self.wordlist = Wordlist('webpath')
	
	@http('GET', '/reports/<int:id>')
	def reports(self, request, id):
		reports = self._db.get_reports(id)
		if reports is None:
			return 404, ''
		return 200, reports
	
	@http('GET', '/task/<int:id>')
	def task(self, request, id):
		task = self._db.get_task(id)
		if task is None:
			return 404, ''
		return 200, task

	@http('GET', '/tasks')
	def tasks(self, request):
		tasks = self._db.get_tasks()
		if tasks is None:
			return 404, ''
		return 200, '{}'.format(tasks)
	
	@http('GET', '/stop/<int:id>')
	def stop(self, request, id):
		pid = self._db.get_task_pid(id)
		if pid is None:
			return 404, ''
		os.system('kill -9 %d'%pid)
		return 200, 'ok'
		
class WebPathBruteService(ApiService):
	name = "webpath_brute_service"
	
	def __init__(self):
		ApiService.__init__(self, 'web-path-brute')
	
	def _exploit(self):
		#time.sleep(1000)
		self._db.update_status(RUNNING)
		if self.wordlist.exists(self._db.task['settings']['wordlist']) is True:
			path_brute = WebPathBrute(self._db.task['settings']['target'], self.wordlist.pops(self._db.task['settings']['wordlist']))
			path_brute.start()
			self._db.save_reports({'reports':path_brute.web_paths, 'error': ''})
		else:
			self._db.save_reports({'reports':[], 'error': 'wordlist not found'})
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
		self._db.update_pid(0)
	
	@http('POST', '/brute/webpath')
	def webpath(self, request):
		self._db.task['settings'] = json.loads(request.get_data(as_text=True))
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		self._db.update_pid(p.pid)
		return 201, json.dumps({'id':id})

class LoginBruteService(ApiService):
	name = "login_brute_service"
	
	def __init__(self):
		ApiService.__init__(self, 'login-brute')
	
	@http('POST', '/brute/login')
	def webpath(self, request):
		print('test')
		return 201, ''