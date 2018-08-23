#!/usr/bin/python 
# -*- coding: utf-8 -*-

import os
import json
import socket
import datetime

from flask_classful import FlaskView, route
from flask import request

from needlebox.scan import Nmap, Masscan
from needlebox.dnsqry import query2, query_types, zonetransfer
from needlebox.net import whois, reverse_whois, location, lookup
from needlebox.bruteforce import WebPathBrute, LoginBrute, DnsBrute

from lib.core.database import Wordlist, Database
from lib.core.task import Process, COMPLETE, RUNNING, STOP, Content

class ApiService(FlaskView):
	
	@route('/reports/<int:id>')
	def reports(self, id):
		reports = self._db.get_reports(id)
		if reports is None:
			return '', 404
		return reports, 200
	
	@route('/task/<int:id>')
	def task(self, id):
		task = self._db.get_task(id)
		if task is None:
			return 404, ''
		return '{}'.format(task), 200

	@route('/tasks')
	def tasks(self):
		return '{}'.format({'tasks':self._db.get_tasks()}), 200
	
	@route('/stop/<int:id>')
	def stop(self, id):
		task = self._db.get_task(id)
		if task is None:
			return '', 404
		if ((id in Content.process_map) is True) and (Content.process_map[id].is_alive() is True):
			Content.process_map[id].stop()
			self._db.task['status'] = STOP
			self._db.task['time']['end'] = str(datetime.datetime.now())
			self._db.update_task(self._db.task)
		return '', 200
	
	@route('/status/<int:id>')
	def status(self, id):
		status = self._db.get_status(id)
		if status is None:
			return '', 404
		return '{}'.format({'status': status}), 200

class LoginBruteService(ApiService):
	
	def __init__(self):
		self._db = Database('login-brute')
		self.wordlist = Wordlist()
	
	def _exploit(self):
		for protocol in self._db.task['settings']['protocols']:
			for proto in protocol:
				login_brute = LoginBrute(proto, target = self._db.task['settings']['target'], users = self.wordlist.pops2(self._db.task['settings']['wordlist']['users']), passwds = self.wordlist.pops2(self._db.task['settings']['wordlist']['passwds']), port = protocol[proto])
				login_brute.start()
				self._db.reports['reports']['login'] = {}
				self._db.reports['reports']['login'][proto] = login_brute.successes
		self._db.save_reports()
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
	
	@route('/brute/login', methods=['POST'])
	def login(self):
		#{"name":"test", "description":"", "target":"172.16.81.173", "protocols":[{"mysql":3306}], "wordlist":{"users":"eeb6151104b9ebf2d4425b6b8ab3b218", "passwds":"3953d58dbd64c6f6627e887bc7d6ff60"}}
		self._db.task['settings'] = request.json
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		Content.process_map[id] = p
		return json.dumps({'id':id}), 201
	

class WebPathBruteService(ApiService):
	
	def __init__(self):
		self._db = Database('webpath-brute')
		self.wordlist = Wordlist()
	
	def _exploit(self):
		self._db.set_status(RUNNING)
		path_brute = WebPathBrute(self._db.task['settings']['target'], self.wordlist.pops(self._db.task['settings']['wordlist']))
		path_brute.start()
		self._db.reports['reports']['webpath'] = path_brute.web_paths
		self._db.save_reports()
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
	
	@route('/brute/webpath', methods=['POST'])
	def webpath(self):
		#{"name":"test", "description":"", "target":"http://172.16.81.173", "wordlist":"e5242135a6402b5de0e92a59890f4d7b"}
		self._db.task['settings'] = request.json
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		Content.process_map[id] = p
		return json.dumps({'id':id}), 201

		
class DnsService(ApiService):
	
	def __init__(self):
		self._db = Database('dns-brute')
		self.wordlist = Wordlist()
	
	def _exploit(self):
		self._db.set_status(RUNNING)
		dns_brute = DnsBrute(self._db.task['settings']['target'], self.wordlist.pops(self._db.task['settings']['wordlist']), ex = self._db.task['settings']['extend'] == 'true')
		dns_brute.start()
		self._db.reports['reports']['dns'] = dns_brute.subdomains_soc
		self._db.save_reports()
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
	
	@route('/brute/dns', methods=['POST'])
	def brute(self):
		#{"name":"test", "description":"", "target":"baidu.com", "wordlist":"03391d79116b09c318e27fee0ed0eb73", "extend": "true"}
		self._db.task['settings'] = request.json
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		Content.process_map[id] = p
		return json.dumps({'id':id}), 201
	
	#/dns/baidu.com/txt?dns=8.8.8.8&port=54&timeout=10
	@route('/dns/<domain>/<type>')
	@route('/dns/<domain>/')
	def query(self, domain, type = 'ANY'):
		type = type.upper()
		if (type in query_types) is False:
			return json.dumps({'error':'%s not supported'%type}), 200
		
		dns_server = request.args.get('dns')
		dns_port = request.args.get('port')
		timeout = request.args.get('timeout')
		dns_server = (dns_server is None) and '114.114.114.114' or dns_server
		dns_port = (dns_port is None) and 53 or int(dns_port)
		timeout = (timeout is None) and 5 or int(timeout)
		try:
			return json.dumps({'dns':{type:query2(domain, type, dns_server = dns_server, dns_port = dns_port, timeout = timeout)}, 'error':''}), 200
		except socket.timeout:
			return json.dumps({'error':'timeout'}), 200
	
	@route('/dns/zonetransfer/<domain>')
	def zonetransfer(self, domain):
		return json.dumps({'dns': {'zonetransfer': zonetransfer(domain)}, 'error': ''}), 200
	
class NmapService(ApiService):
	
	def __init__(self):
		self._db = Database('nmap-scan')
	
	def _exploit(self):
		self._db.set_status(RUNNING)
		self._db.reports['reports'] = Nmap().scan(self._db.task['settings']['target'], self._db.task['settings']['ports'], ' '.join(self._db.task['settings']['option']))
		self._db.save_reports()
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
	
	@route('/scan/nmap', methods=['POST'])
	def nmap(self):
		#{"name":"test", "description":"", "target":"172.16.80.125", "ports":"22,443-2000", "option":["-sV","-T4"]}
		self._db.task['settings'] = request.json
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		Content.process_map[id] = p
		return json.dumps({'id':id}), 201

class MasscanService(ApiService):
	
	def __init__(self):
		self._db = Database('masscan-scan')
	
	def _exploit(self):
		self._db.set_status(RUNNING)
		self._db.reports['reports'] = Masscan().scan(self._db.task['settings']['target'], self._db.task['settings']['ports'], '--rate=%d'%self._db.task['settings']['rate'] + ' '.join(self._db.task['settings']['option']))
		self._db.save_reports()
		self._db.task['time']['end'] = str(datetime.datetime.now())
		self._db.task['status'] = COMPLETE
		self._db.update_task()
	
	@route('/scan/masscan', methods=['POST'])
	def masscan(self):
		#{"name":"test", "description":"", "target":"172.16.80.125", "ports":"22,443-2000", "rate":1000, "option":["--banner"]}
		self._db.task['settings'] = request.json
		self._db.task['time']['start'] = str(datetime.datetime.now())
		id = self._db.save_task()
		p = Process(target = self._exploit)
		p.start()
		Content.process_map[id] = p
		return json.dumps({'id':id}), 201

class NetService(FlaskView):
	
	@route('/net/whois/<target>')
	def whois(self, target):
		w = whois(target)
		if w is None : w = {}
		return json.dumps({'net':{'whois':w}, 'error':''}), 200
	
	@route('/net/rwhois/<target>')
	def reverse_whois(self, target):
		rw = reverse_whois(target)
		if rw is None: rw = []
		return json.dumps({'net':{'rwhois':rw}, 'error':''})
	
	@route('/net/location/<target>')
	def location(self, target):
		try:
			l = location(target)
			if l is None: l = []
			return json.dumps({'net':{'location':l}, 'error':''}), 200
		except socket.gaierror:
			return json.dumps({'net':{'location':[]}, 'error':''}), 200
	
	@route('/net/lookup/<target>')
	def lookup(self, target):
		l = lookup(target)
		if l is None: l = {}
		return json.dumps({'net':{'lookup':l}, 'error':''}), 200