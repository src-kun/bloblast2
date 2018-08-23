#!/usr/bin/python 
# -*- coding: utf-8 -*-

from flask import Flask, render_template

from lib.core.api import *

app = Flask(__name__)

LoginBruteService.register(app, route_base='/')
WebPathBruteService.register(app, route_base='/')
DnsService.register(app, route_base='/')
NmapService.register(app, route_base='/')
MasscanService.register(app, route_base='/')
NetService.register(app, route_base='/')

# If we're running in stand alone mode, run the application
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8888, debug=False)