#!/usr/bin/python 
# -*- coding: utf-8 -*-

import hashlib

def md5(text):
	hash = hashlib.md5()
	hash.update(text.encode(encoding='utf-8'))
	return hash.hexdigest()

def file_md5(filename, blocksize = 65536):
	hash = hashlib.md5()
	with open(filename, "rb") as f:
		for block in iter(lambda: f.read(blocksize), b""):
			hash.update(block)
	return hash.hexdigest()
