#!/usr/bin/python 
# -*- coding: utf-8 -*-

import json
import datetime

from redis import Redis, ConnectionPool

from lib.utils.common import md5, file_md5

class RedisEx(Redis):
	
	copy_key_lua = """
						local src = KEYS[1]
						local des = KEYS[2]

						if redis.call("EXISTS", des) == 1 then
							if type(ARGV[1]) == "string" and ARGV[1]:upper() == "NX" then
								return nil
							else
								redis.call("DEL", des)
							end
						end

						redis.call("RESTORE", des, 0, redis.call("DUMP", src))
						return "OK"
				"""
	
	def copy(self, src, des):
		return self.register_script(RedisEx.copy_key_lua)(keys = [src, des])

def redis_pool(ip, db, port = 6379, password = None, decode_responses = True):
	return ConnectionPool(host = ip, port = port, password = password, db = db, decode_responses = decode_responses)

#redis main pool
_redis_pool_main = redis_pool('127.0.0.1', 0)

#wordlist db pool
_redis_pool_1 = redis_pool('127.0.0.1', 1)

#task info
_redis_pool_2 = redis_pool('127.0.0.1', 2)

class Wordlist():
	
	KEY = 'wordlist'
	WORDLIST_MD5_KEY = 'wordlist-md5'
	
	def __init__(self):
		self.redis = RedisEx(connection_pool = _redis_pool_1)
		self.main_redis = RedisEx(connection_pool = _redis_pool_main)
		self.block = 2048
	
	def exists(self, key):
		return self.redis.exists(key)
	
	def puts(self, filename, weight = 0, mark = ''):
		fp = None
		size = 0
		read_point = 0
		key = file_md5(filename)
		if self.exists(key) is False:
			try:
				fp = open(filename, 'r')
				while True:
					read_point += self.block
					lines = fp.read(self.block)
					if lines is '': break
					arry_line = lines.split('\n')
					if len(lines) == self.block:
						find_index = lines.rfind('\n')
						if (lines[-1] != '\n') and (find_index != -1):
							read_point -= self.block - find_index - 1
							fp.seek(read_point)
							arry_line.pop()
					else:
						size = read_point + len(lines) - self.block
					self.redis.sadd(key, *arry_line)
				self.redis.set(key + "-detail", {"key": key, "property": {"file_size": size, "word_len": self.redis.scard(key), "date": str(datetime.datetime.now()), "weight": weight, "mark": mark}})
			finally:
				if fp: fp.close()
		return json.loads(self.redis.get(key + '-detail').replace("'", '"'))
	
	def pops(self, key):
		if self.exists(key) is True:
			des_key = '%s-pop-%s'%(key, str(datetime.datetime.now()))
			try:
				self.redis.copy(key, des_key)
				len = self.redis.scard(des_key)
				
				for i in range(int(len / self.block) + 1):
					wordlist = self.redis.spop(des_key, self.block)
					for word in wordlist:
						yield word
			finally:
				if self.exists(des_key) is True: self.redis.delete(des_key)
		else:
			yield ''
	
	def pops2(self, key):
		if self.exists(key) is False: return []
		len = self.redis.scard(key)
		if len > 1000000:
			#TODO
			raise Exception('DB content is out of range: 1000000')
		return self.redis.smembers(key)

class Database():
	
	TASK_INDEX_KEY = 'all-task'
	
	def __init__(self, key = None):
		self.redis = RedisEx(connection_pool = _redis_pool_2)
		self.key = key
		self.task = {'settings': {}, 'time':{'start':'', 'end':''}, 'history': [], 'status': 0, 'last':''}
		self.reports = {'reports': {}, 'error': ''}
	
	def save_task(self):
		#report key
		self.task['report_key'] = md5(json.dumps(self.task) + str(datetime.datetime.now()))
		#record current task info to tasks
		self.task['id'] = self.redis.lpush(self.key, self.task)
		#record last task key
		self.task['last'] = self.task['report_key']
		#record current task id and key to TASK_INDEX_KEY
		self.task['task_id'] = self.redis.lpush(Database.TASK_INDEX_KEY, {'id':self.task['id'], 'key': self.key})
		#init report
		self.redis.set(self.task['report_key'], {'reports':{}, 'error': ''})
		self.redis.lset(self.key, -self.task['id'], self.task)
		return self.task['task_id']
	
	def _get_task_index(self, task_id):
		task = self.redis.lindex(Database.TASK_INDEX_KEY, -task_id)
		if task: return json.loads(task.replace("'", '"'))
	
	def update_task(self, task = None):
		if task is None:
			return self.redis.lset(self.key, -self.task['id'], self.task)
		else:
			task_index = self._get_task_index(task['task_id'])
			if task_index: return self.redis.lset(task_index['key'], -task['id'], task)
	
	def _get_task(self, key, id):
		return json.loads(self.redis.lindex(key, -id).replace("'", '"'))
	
	def get_task(self, id):
		task_index = self._get_task_index(id)
		if task_index:
			self.task = self._get_task(task_index['key'], task_index['id'])
			return self.task
	
	def get_tasks(self):
		tasks = []
		length = self.redis.llen(Database.TASK_INDEX_KEY)
		if length == 0: return []
		for id in range(length):
			tasks.append(self.get_task(id))
		return tasks
	
	def set_status(self, status):
		self.task['status'] = status
		return self.redis.lset(self.key, -self.task['id'], self.task)
	
	def get_status(self, id):
		if self.get_task(id): return self.task['status']
	
	def save_reports(self):
		self.redis.set(self.task['report_key'], self.reports)
	
	def get_reports(self, id):
		if self.get_task(id): return self.redis.get(self.task['report_key'])
			

	