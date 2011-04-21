import threading,thread
import subprocess 
import httplib
import json
import re
import time
import ctypes
import sys
import os
from HTMLParser import HTMLParser

class MyHTMLParser(HTMLParser):
	links=[]
	links_with_dir=[]
	def handle_starttag(self, tag, attrs):
		if tag == 'a':
			a_link = attrs[0][1]
			if a_link.endswith('avi'):
				self.links.append(a_link)
		
	def set_links_with_dir(self, dir):
		for entry in self.links:
			self.links_with_dir.append(dir+entry)
		return self.links_with_dir

BINARY_CURL = "C:/CURL/curl.exe"
BINARY_WGET = "C:/Program Files/GnuWin32/bin/wget.exe"
LOCAL_DIR = "C:/tmp/"
username="kyle"
password="Schinkel123$$"

full_dl_path = "http://brain.tekzor.com/rutorrent/files//Bleach%20season%206/"

m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", full_dl_path)
mvals = m.groupdict()
if mvals['port'] is None:
	mvals['port'] = 80

OUT_list = mvals['path'].split('/')
OUT = OUT_list.pop()
OUT = OUT.replace('%20',' ')
OUT = LOCAL_DIR+OUT
basic_auth = username + ":"+password
encoded = basic_auth.encode("base64")[:-1]
headers = {"Authorization":"Basic %s" % encoded}
params = ""
conn = httplib.HTTPConnection(mvals['host'],mvals['port'])
conn.request('GET',mvals['path'],params,headers);
responce = conn.getresponse()
size = responce.getheader("content-length")
if full_dl_path.endswith('/'):
	full_html_page = responce.read()
	myparser  = MyHTMLParser()
	myparser.feed(full_html_page)
	for entry in myparser.set_links_with_dir(full_dl_path):
		print entry

#Os.listdir