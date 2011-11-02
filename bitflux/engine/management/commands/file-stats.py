from django.core.management.base import BaseCommand, CommandError
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import Job
from bitflux.engine.models import UserProfile
from bitflux.engine.models import deamon
from bitflux.engine.models import autoDLer
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import log
from bitflux.engine.management.commands import common
from django.conf import settings
import subprocess 
import time
import datetime
import os
import sys
import ctypes
import time
import signal
from datetime import timedelta
import re
import threading,thread
import httplib
import urllib
import xmlrpclib
import random, string
import traceback
try:
    import json
except ImportError:
    import simplejson as json
from HTMLParser import HTMLParser


def log_to_file(msg):
    f = open("file-stats.log", 'a')
    f.write(str(datetime.datetime.now())+": "+msg+"\n")
    f.close


def rename(a_job):
    log_to_file("Attempting to rename: " + a_job.filename)
    show_name = common.is_tv_show(a_job.filename)
    if len(show_name) > 0:
       a_job.filename = common.name_wrapper(show_name)
       #a_job.filename = unicode(show_name, errors='ignore')
    else:
        movie_name = common.is_movie(a_job.filename)
        if len(movie_name) > 0:
                a_job.filename = common.name_wrapper(movie_name)
    a_job.autorename = False
    a_job.save()

def file_stats(id):
    a_job = Job.objects.get(id=int(id))
    if a_job.autorename == True:
        rename(a_job)
        
    log_to_file("Retrieving stats for: " + a_job.filename)
    status, filename, size = common.getEntryInfo(a_job.full_url)
    a_job.total_size = size
    a_job.display_size = common.convert_bytes(a_job.total_size)
    
    log_to_file("Updating status for: " + a_job.filename)
    if a_job.status.endswith('Queue'):
        a_job.status = 'Queued'
    elif a_job.status.endswith('Stop'):
        a_job.status = 'Stopped'
    elif a_job.status.endswith('Start'):
        a_job.status = 'Starting...'
    a_job.save()    
    log_to_file("Finished with for: " + a_job.filename)    
        
class Command(BaseCommand):
    def handle(self, *args, **options):
        if len(args) != 1:
            log_to_file("invalid number of arguments!")
            exit(-1)

        log_to_file("getting file stats for job id: " + args[0])
        file_stats(args[0])