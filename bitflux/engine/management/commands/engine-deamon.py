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

seed = str(random.random()) + random.choice(string.letters)
XML_RPC_PASS = seed
seed = random.choice(string.letters) + str(random.random())
XML_RPC_USER = seed
ARIA2C_ARGS = ['aria2c','-q',
                '--max-tries=0',
                '--enable-rpc=true',
                '--rpc-listen-all=true',
                '--rpc-user='+XML_RPC_USER,
                '--rpc-passwd='+XML_RPC_PASS,
                '--max-connection-per-server=10']
#ARIA2C_ARGS = ['aria2c','--enable-rpc=true','--xml-rpc-listen-all=true','--xml-rpc-user='+XML_RPC_USER,'--xml-rpc-passwd='+XML_RPC_PASS]
#aria2c --enable-rpc=true --rpc-listen-all=true --rpc-user=test --rpc-passwd=test
#'--max-connection-per-server=10'
#'--max-download-result=0'
ARIA2C = subprocess.Popen(ARIA2C_ARGS,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
def log_to_file(msg):
    f = open(settings.ENGINE_LOG, 'a')
    f.write(str(datetime.datetime.now())+": "+msg+"\n")
    f.close

    
def getETA(total, already_dled, speed):
    if already_dled == 0 or speed == 0:
        #cannot calculate at this time
        return 0
    dif = float(total) - float(already_dled)
    ETA = dif / float(speed)
    return ETA


def loadDirectory(job):
    #URLDirectory,status,request,autoRename):
    #extract the values we need later
    myparser  = common.MyHTMLParser()
    myparser.set_parent_job(job)
    
    URLDirectory = job.full_url
    autoRename = job.autorename
    status = job.status
    local_dir = job.local_directory 
    #remove the directory entry
    deleteJob(job)
    log_to_file("Attempting to load files from remote directory: " + URLDirectory)
    #continue to parse directory for entries
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", URLDirectory)
    mvals = m.groupdict()
    if mvals['port'] is None:
        mvals['port'] = 80
        if mvals['type'] == 'https':
            mvals['port'] = 443
    basic_auth = settings.USERNAME + ":"+settings.PASSWORD
    encoded = basic_auth.encode("base64")[:-1]
    headers = {"Authorization":"Basic %s" % encoded}
    params = ""
    
    try:
        if mvals['type'] == 'https':
            conn = httplib.HTTPSConnection(mvals['host'],mvals['port'], timeout=10)
        else:
            conn = httplib.HTTPConnection(mvals['host'],mvals['port'], timeout=10)
        conn.request('GET',mvals['path'],params,headers);
        responce = conn.getresponse()
        fullhtmlpage = responce.read()
        conn.close()
        myparser.feed(fullhtmlpage)
    except Exception,e:
        log_to_file("Failed to load directory: " + URLDirectory)
        return

    for entry in myparser.set_links_with_dir(URLDirectory):
        OUT_list = entry.split('/')
        filename = OUT_list.pop()
        filename = urllib.unquote(filename)
        log_to_file("Entry in directory found:" + filename)
        
        try:
            responce, filename, size = common.getEntryInfo(entry)
        except:
            size = -1
        out_list = mvals['path'].split('/')
        dir = out_list.pop()
        dir = out_list.pop()
        dir = urllib.unquote(dir)


        entry = urllib.unquote(entry)
        m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", entry)
        mvals = m.groupdict()
        full_dl_path = mvals['type']+'://' + mvals['host'] + urllib.quote(mvals['path'] )
        
        #out = profile.dl_dir+filename
        new_job = Job()
        
        if autoRename:
            #Add renamer code here
            new_job.autorename = False
            show_name = common.is_tv_show(filename)
            if len(show_name) > 0:
                filename = show_name
        if status.endswith('Queue'):
            status = 'Queued'
        elif status.endswith('Stop'):
            status = 'Stopped'
        elif status.endswith('Start'):
            status = 'Starting...'
        
        #filename = unicode(filename, errors='ignore')
        new_job.status = status
        new_job.queue_id = len(Job.objects.all())
        new_job.gid = -1
        new_job.process_pid = -1
        new_job.dl_speed = 0
        new_job.time_seg_start = -1
        new_job.time_seg_end = -1
        new_job.display_size = common.convert_bytes(size)
        new_job.total_size = size
        new_job.dled_size = 0
        #new_job.dled_dif_size = 0; removed
        new_job.full_url = full_dl_path
        new_job.local_directory = local_dir
        new_job.filename = common.name_wrapper(filename)
        new_job.notes = "CURL download: " + new_job.local_directory + new_job.filename
        new_job.progress = 0;
        new_job.eta = "";
        new_job.save()
    myparser.close()
    
def fixEntriesAfter(fix_queue_id):
    for a_job in Job.objects.all().order_by('queue_id'):
        if a_job.queue_id > fix_queue_id:
            a_job.queue_id = a_job.queue_id -1
            a_job.save()
    
def deleteJob(a_job):
    if a_job.gid != -1:
        try:
            #s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
            s.aria2.remove(str(a_job.gid))
        except Exception,e:
            log_to_file("aria2: failed to remove "+str(a_job.gid)+" "+a_job.filename)
    log_to_file("Removed job with queue id: "+str(a_job.queue_id))
    a_job.delete()

def pauseJob(job):
    if job.gid != -1:
        try:
            #s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
            s.aria2.pause(str(job.gid))
            log_to_file("Pausing: "+str(job.gid))
        except Exception,e:
            log_to_file("Cannot pause"+str(job.gid)+" "+job.filename)
    else:
        log_to_file("Tried to stop download with invalid gid!"+job.filename)
            
def startJob(job):
    if job.gid == -1:
        #s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
        options = {"dir":job.local_directory,
                    "out":job.filename,
                    "http-passwd":settings.PASSWORD,
                    "http-user":settings.USERNAME,
                    "file-allocation":'none'
                    }
        gid = s.aria2.addUri([job.full_url],options)
        job.gid = int(gid)
    else:
        #s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
        s.aria2.unpause(str(job.gid))
        
    job.status="Running"
    job.save()
    log_to_file("Started job: "+str(job.gid)+"   name:"+job.filename)

    
def runEngine():
    jobs_deleted = False
    
    for a_job in Job.objects.filter(status__startswith='Deleting'):
        jobs_deleted = True
        path_to_delete = a_job.local_directory + a_job.filename
        status = a_job.status
        gid = a_job.gid
        deleteJob(a_job) 
        if status == 'Deleting With Data...':
            if gid != -1:
                try:
                    os.remove(path_to_delete)
                    os.remove(path_to_delete + ".aria2")
                except Exception,e:
                    log_to_file("Failed to delete files: " + str(e))
        log_to_file("Deleted: " + path_to_delete)
        
        
    for a_job in Job.objects.filter(status__startswith='New'):
        log_to_file('new job found')
        if a_job.full_url.endswith('/'):
            #load directory
            jobs_deleted = True
            loadDirectory(a_job)
            continue #continue, because this specific job is going to be deleted, and more created
        elif a_job.autorename:
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
        status, filename, size = common.getEntryInfo(a_job.full_url)
        a_job.total_size = size
        a_job.display_size = common.convert_bytes(a_job.total_size)
        a_job.save()
        if a_job.status.endswith('Queue'):
            a_job.status = 'Queued'
            a_job.save()
        elif a_job.status.endswith('Stop'):
            a_job.status = 'Stopped'
            a_job.save()
        elif a_job.status.endswith('Start'):
            a_job.status = 'Starting...'
            a_job.save()

            

    if jobs_deleted:
        reorder =0 
        for a_job in Job.objects.all().order_by('queue_id'):
                a_job.queue_id = reorder
                a_job.save()
                reorder += 1
    num_dls_at_once = 1
    num_dls = 0
 
    for a_job in Job.objects.filter(status='Running'):
        num_dls = num_dls +1
        stats = s.aria2.tellStatus(str(a_job.gid),['gid','downloadSpeed','completedLength','status','connections'])
        a_job.dl_speed = int(stats['downloadSpeed'])
        a_job.dled_size = int(stats['completedLength'])
        progress = (float(a_job.dled_size)/float(a_job.total_size))*100
        if progress >= 100:
            a_job.progress = 100
            a_job.status = 'Finished'
            a_job.dl_speed=0
            a_job.process_pid=-1
        else:
            a_job.progress = progress
        ETA = getETA(a_job.total_size, a_job.dled_size,  a_job.dl_speed)
        a_job.eta = common.convert_time(ETA)
        a_job.save()
    
    for a_job in Job.objects.filter(status='Starting...'):
        startJob(a_job)
    
    for a_job in Job.objects.filter(status='Stopping...'):
        pauseJob(a_job)
        a_job.process_pid = -1
        a_job.dl_speed=0
        a_job.status="Stopped"
        a_job.eta = ""
        log_to_file("Stopped: "+str(a_job.queue_id)+" "+a_job.filename)
        a_job.save()
    
    for a_job in Job.objects.filter(status='Queued').order_by('queue_id'):
        if num_dls < num_dls_at_once:
            startJob(a_job)
            num_dls = num_dls +1

            
    for cleanup in deamon.objects.all():
                cleanup.delete()
    os.environ['TZ'] = 'US/Eastern'
    engineStatus = deamon()
    engineStatus.process_pid = os.getpid()
    engineStatus.ts = datetime.datetime.now()
    engineStatus.save()
            
class Command(BaseCommand):
    def handle(self, *args, **options):
        print "Now running... View",settings.ENGINE_LOG,"for more information"
        for a_job in Job.objects.all():
            if a_job.gid != -1:
                a_job.gid = -1
                if a_job.status == "Running":
                    a_job.status = "Queued"
                a_job.save()

        try:
            while(1):
                runEngine()
                time.sleep(1)
        except Exception,e:
            print traceback.print_exc()
            log_to_file(str(e))
            if sys.platform == "win32":
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, ARIA2C.pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(ARIA2C.pid, signal.SIGKILL)
            exit()
                
        
