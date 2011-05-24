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
    URLDirectory = job.full_url
    autoRename = job.autorename
    status = job.status
    local_dir = job.local_directory 
    #remove the directory entry
    jobs = []
    jobs.append(job)
    deleteJobs(jobs)
    #continue to parse directory for entries
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", URLDirectory)
    mvals = m.groupdict()
    if mvals['port'] is None:
        mvals['port'] = 443
    basic_auth = settings.USERNAME + ":"+settings.PASSWORD
    encoded = basic_auth.encode("base64")[:-1]
    headers = {"Authorization":"Basic %s" % encoded}
    params = ""
    conn = httplib.HTTPSConnection(mvals['host'],mvals['port'])
    conn.request('GET',mvals['path'],params,headers);
    responce = conn.getresponse()
    fullhtmlpage = responce.read()
    conn.close()
    myparser  = common.MyHTMLParser()
    myparser.feed(fullhtmlpage)
    first =0
    for entry in myparser.set_links_with_dir(URLDirectory):
        OUT_list = entry.split('/')
        filename = OUT_list.pop()
        filename = urllib.unquote(filename)

        try:
            status, filename, size = common.getEntryInfo(entry)
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
        new_job.filename = filename 
        new_job.notes = "CURL download: " + new_job.local_directory + filename
        new_job.progress = 0;
        new_job.eta = "";
        new_job.save()

    
def fixEntriesAfter(fix_queue_id):
    for a_job in Job.objects.all().order_by('queue_id'):
        if a_job.queue_id > fix_queue_id:
            a_job.queue_id = a_job.queue_id -1
            a_job.save()
    
def deleteJobs(jobs):
    for a_job in jobs:
        a_job.delete()
        s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
        s.aria2.remove(str(job.gid))
        log_to_file("Removed job with queue id: "+str(a_job.queue_id))
    jobs.reverse()
    for a_job in jobs:
        fixEntriesAfter(a_job.queue_id)

def killJob(job):
    if job.gid != -1:
        try:
            s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
            s.aria2.pause(str(job.gid))
            log_to_file("Pausing: "+str(job.gid))
        except Exception,e:
            log_to_file("Cannot pause"+str(job.gid)+" "+job.filename)
    else:
        log_to_file("Tried to stop download with invalid gid!"+job.filename)
    '''if pid != -1:
        try:
            if sys.platform == "win32":
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            log_to_file("Process: "+str(pid)+" does not exsist")'''
            
def startJob(job):
    if job.gid == -1:
        s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
        options = {"dir":job.local_directory,
                    "out":job.filename,
                    "http-passwd":settings.PASSWORD,
                    "http-user":settings.USERNAME,
                    "file-allocation":'none'
                    }
        gid = s.aria2.addUri([job.full_url],options)
        job.gid = int(gid)
        job.status="Running"
        job.save()
    else:
        s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
        s.aria2.unpause(str(job.gid))
        job.status="Running"
        job.save()

    '''URL = job.full_url.replace('://','://'+settings.USERNAME+":"+settings.PASSWORD+"@")
    local_path = job.local_directory + job.filename'''
    log_to_file("Started job: "+str(job.gid)+"   name:"+job.filename)
    #WGET_ARGS = ['wget','-c','-q','--user='+settings.USERNAME,'--password='+settings.PASSWORD,'--no-check-certificate',URL,'--output-document='+local_path]
    #process = subprocess.Popen(WGET_ARGS,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    #aria2c_args = ['aria2c','-c','-q','--file-allocation=none','--http-user='+settings.USERNAME,'--http-passwd='+settings.PASSWORD,'-d',job.local_directory,URL]
    #CURL_ARGS = ['curl','-u',settings.USERNAME+':'+settings.PASSWORD,'-C','-','-s',URL,'-o',local_path]
    
    '''AXEL_ARGS = ['axel','-q',URL,'-o',local_path]
    process = subprocess.Popen(AXEL_ARGS,stdout=subprocess.PIPE,stderr=subprocess.PIPE)'''
    #aria2c -c --file-allocation=none --http-user=kschinkel --http-passwd=Schinkel123 -d /mnt/Data/incoming http://kschinkel.ferret.feralhosting.com/rutorrent/DATA/Family.Guy.S09E18.Its.a.Trap.HDTV.XviD-LOL.avi
    
    #curl -u kschinkel:Schinkel123 -C - http://kschinkel.ferret.feralhosting.com/rutorrent/DATA/South.Park.S15E04.T.M.I.UNCENSORED.HDRiP.XviD-T00NG0D.avi -O
    # curl -u kschinkel:Schinkel123 -C - http://kschinkel.ferret.feralhosting.com/rutorrent/DATA/South.Park.S15E04.T.M.I.UNCENSORED.HDRiP.XviD-T00NG0D.avi -o /mnt/Data/incoming/test.avi
    #axel -q http://kschinkel:Schinkel123@kschinkel.ferret.feralhosting.com/rutorrent/DATA/South.Park.S15E04.T.M.I.UNCENSORED.HDRiP.XviD-T00NG0D.avi -o /mnt/Data/incoming/test.avi
    #axel -q http://kschinkel:Schinkel123kschinkel.ferret.feralhosting.com/rutorrent/DATA/South.Park.S15E04.T.M.I.UNCENSORED.HDRiP.XviD-T00NG0D.avi -o /mnt/Data//incoming/South.Park.S15E04.T.M.I.UNCENSORED.HDRiP.XviD-T00NG0D.avi
    
    '''
           --http-user=USER
           Set HTTP user. This affects all URIs.

       --http-passwd=PASSWD
           Set HTTP password. This affects all URIs.
        -c continue
        
        -d directory'''
    
def runEngine():
    for cleanup in deamon.objects.all():
            cleanup.delete()
    os.environ['TZ'] = 'US/Eastern'
    engineStatus = deamon()
    engineStatus.process_pid = os.getpid()
    engineStatus.ts = datetime.datetime.now()
    engineStatus.save()
    
    num_dls_at_once = 1
    num_dls = 0
    tobeDel = []
    reorder =0 
    for a_job in Job.objects.all().order_by('queue_id'):
        a_job.queue_id = reorder
        a_job.save()
        reorder += 1
        if a_job.status.startswith('New'):
            log_to_file('new job found')
            if a_job.full_url.endswith('/'):
                #load directory
                loadDirectory(a_job)
                continue #continue, because this specific job is going to be deleted, and more created
            elif a_job.autorename:
                show_name = common.is_tv_show(a_job.filename)
                if len(show_name) > 0:
                   a_job.filename = show_name
                   #a_job.filename = unicode(show_name, errors='ignore')
                else:
                    movie_name = common.is_movie(a_job.filename)
                    if len(movie_name) > 0:
                            a_job.filename = movie_name
                            #a_job.filename = unicode(movie_name, errors='ignore') 
                    '''else:
                        parent_dir = urllib.unquote(parent_dir)
                        movie_name = is_movie(parent_dir)
                        if len(movie_name) > 0:
                            a_job.filename = movie_name'''
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
        
    for a_job in Job.objects.all().order_by('queue_id'):
    
        if a_job.status == 'Running':
            s = xmlrpclib.ServerProxy('http://' + XML_RPC_USER + ':' + XML_RPC_PASS + '@localhost:6800/rpc')
            stats = s.aria2.tellStatus(str(a_job.gid))
            a_job.dl_speed = int(stats['downloadSpeed'])
            a_job.dled_size = int(stats['completedLength'])
            a_job.progress = (float(a_job.dled_size)/float(a_job.total_size))*100
            ETA = getETA(a_job.total_size, a_job.dled_size,  a_job.dl_speed)
            a_job.eta = common.convert_time(ETA)
            a_job.save()
            '''if os.path.exists(a_job.local_directory + a_job.filename):
                dled_size_str = os.path.getsize(a_job.local_directory + a_job.filename)
                dled_size_int = int(dled_size_str)#/1048576
                #a_job.dled_size = dled_size_int
                try:
                    a_job.progress = (float(dled_size_int)/float(a_job.total_size))*100
                except:
                    log_to_file("Progress calculation failed!")
                    progress = 0
                #time_seg_end = time.clock()
                #time_seg_end = float(time.ctime())
                a_job.time_seg_end = time.time()
                dif_data = dled_size_int - a_job.dled_size
                time_dif = a_job.time_seg_end - a_job.time_seg_start
                if time_dif > 0:
                    try:
                        a_job.dl_speed = (dif_data/time_dif)
                    except:
                        log_to_file("DL Speed calculation failed!")
                        a_job.dl_speed = -1
                    a_job.time_seg_start = a_job.time_seg_end
                #a_job.dled_dif_size = a_job.dled_size           dled_dif_size was removed
                a_job.dled_size = dled_size_int
                
                #Calc ETA
                ETA = getETA(a_job.total_size, a_job.dled_size,  a_job.dl_speed)
                a_job.eta = common.convert_time(ETA)
                a_job.save()
            else:
                log_to_file("Cannot find file: "+a_job.local_directory + a_job.filename+" to compute stats for")'''

        if a_job.progress ==100 and a_job.status !='Finished' and a_job.status != 'Deleting...' and a_job.status != 'Deleting With Data...':
            a_job.status = 'Finished'
            a_job.dl_speed=0
            a_job.process_pid=-1
            a_job.save()
        
        if a_job.status == 'Starting...':
            startJob(a_job)
            #a_job.status = "Running"
            #a_job.save()
        
        elif a_job.status == 'Stopping...':
            killJob(a_job)
            a_job.process_pid = -1
            a_job.dl_speed=0
            a_job.status="Stopped"
            a_job.eta = ""
            log_to_file("Stopped: "+str(a_job.queue_id)+" "+a_job.filename)
            a_job.save()
        
        elif a_job.status == 'Deleting...' or a_job.status == 'Deleting With Data...':
            killJob(a_job)
            #tobeDel.append(a_job)
            if a_job.status == 'Deleting With Data...':
                try:
                    os.remove(a_job.local_directory + a_job.filename)
                except OSError:
                    if a_job.dled_size != 0:
                        log_to_file("Could not remove data for file: " + a_job.local_directory + a_job.filename)
            log_to_file("Deleting: " + a_job.filename)
            a_job.delete()        
        elif a_job.status == 'Running':
            num_dls = num_dls +1
        elif a_job.status == "Queued" and num_dls < num_dls_at_once:
            startJob(a_job)
            #a_job.status = "Running"
            #a_job.save()
            num_dls = num_dls +1
    #deleteJobs(tobeDel)

class Command(BaseCommand):
    args = '<poll_id poll_id ...>'
    help = 'Closes the specified poll for voting'
    def handle(self, *args, **options):
        print "Now running... View",settings.ENGINE_LOG,"for more information"
        for a_job in Job.objects.all():
            if a_job.status == "Running" or a_job.status == "Starting..." :
                a_job.gid = -1
                a_job.status = "Stopped"
                a_job.save()
        test = "test"
        #test = test.encode("base64")[:-1]
        ARIA2C_ARGS = ['aria2c','-q','--enable-xml-rpc=true','--xml-rpc-listen-all=true','--xml-rpc-user='+XML_RPC_USER,'--xml-rpc-passwd='+XML_RPC_PASS]
        aria2c = subprocess.Popen(ARIA2C_ARGS,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            while(1):
                #try:
                runEngine()
                time.sleep(1)
                #except Exception,e:
                 #   log_to_file(str(e))
        except Exception,e:
            print traceback.print_exc()
            log_to_file(str(e))
            if sys.platform == "win32":
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, aria2c.pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(aria2c.pid, signal.SIGKILL)
            exit()
                
        
