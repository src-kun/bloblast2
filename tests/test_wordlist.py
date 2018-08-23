#!/usr/bin/python 
# -*- coding: utf-8 -*-
from lib.core.database import Wordlist

wl = Wordlist()
print(wl.puts('dir.txt'))
print(wl.puts('user.list'))
print(wl.puts('password.list'))
print(wl.puts('small.list'))

