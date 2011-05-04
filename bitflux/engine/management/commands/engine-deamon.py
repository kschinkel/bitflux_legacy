from django.core.management.base import BaseCommand, CommandError
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import Job
from bitflux.engine.models import UserProfile
from bitflux.engine.models import deamon
from bitflux.engine.models import autoDLer
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import log
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
try:
    import json
except ImportError:
    import simplejson as json
from HTMLParser import HTMLParser

class MyHTMLParser(HTMLParser):
    links=[]
    links_with_dir=[]
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            a_link = attrs[0][1]
            if a_link.endswith('.avi') or a_link.endswith('.mp3') or a_link.endswith('.mpg') or a_link.endswith('.rar') or a_link.endswith('.zip') or a_link.endswith('.nfo') or a_link.endswith('.sfv'):
                self.links.append(a_link)
            else:
                is_rar_archieve = re.match(".*\.r[0-9]*$", a_link)
                if is_rar_archieve is not None:
                   self.links.append(a_link)
    def set_links_with_dir(self, dir):
        for entry in self.links:
            sep_link =  entry.split('/')
            filename = sep_link[len(sep_link)-1]
            #filename = urllib.quote(filename)
            self.links_with_dir.append(dir+filename)
        return self.links_with_dir
        
def log_to_file(msg):
    f = open(settings.ENGINE_LOG, 'a')
    f.write(str(datetime.datetime.now())+": "+msg+"\n")
    f.close

def convert_bytes(bytes):
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fTB' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fGB' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fMB' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fKB' % kilobytes
    else:
        size = '%.2fB' % bytes
    return size

def convert_time(seconds):
    seconds = float(seconds)
    if seconds >= 31556926:
        years = seconds / 31556926
        format = '%.2fy' % years
    elif seconds >= 2629743.83:
        months = seconds / 2629743.83
        format = '%.2fM' % months
    elif seconds >= 604800:
        weeks = seconds / 604800
        format = '%.2fw' % weeks
    elif seconds >= 86400:
        days = seconds / 86400
        format = '%.2fd' % days
    elif seconds >= 3600:
        hours = seconds / 3600
        format = '%.2fh' % hours
    elif seconds >= 60:
        minutes = seconds /  60
        format = '%.2fm' % minutes
    else:
        format = '%.2fs' % seconds    
    return format  
    
def getETA(total, already_dled, speed):
    if already_dled == 0 or speed == 0:
        #cannot calculate at this time
        return 0
    dif = float(total) - float(already_dled)
    ETA = dif / float(speed)
    return ETA

def getContentLength(URL):
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", URL)
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
    size = responce.getheader("content-length")
    conn.close()
    return size
    
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
    myparser  = MyHTMLParser()
    myparser.feed(fullhtmlpage)
    first =0
    for entry in myparser.set_links_with_dir(URLDirectory):
        OUT_list = entry.split('/')
        filename = OUT_list.pop()
        filename = urllib.unquote(filename)

        try:
            size = getContentLength(entry)
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
            show_name = is_tv_show(filename)
            if len(show_name) > 0:
                filename = show_name
        if status.endswith('Queue'):
            status = 'Queued'
        elif status.endswith('Stop'):
            status = 'Stopped'
        elif status.endswith('Start'):
            status = 'Starting...'
        

        new_job.status = status
        new_job.queue_id = len(Job.objects.all())
        new_job.process_pid = -1
        new_job.dl_speed = 0
        new_job.time_seg_start = -1
        new_job.time_seg_end = -1
        new_job.display_size = convert_bytes(size)
        new_job.total_size = size
        new_job.dled_size = 0
        #new_job.dled_dif_size = 0; removed
        new_job.full_url = full_dl_path
        new_job.local_directory = local_dir
        new_job.filename = filename 
        new_job.notes = "CURL download: " + new_job.local_directory + new_job.filename
        new_job.progress = 0;
        new_job.eta = "";
        new_job.save()


def get_espisode_info(name, season, episode):
    name = name.replace(" ","%20")
    #http://services.tvrage.com/tools/quickinfo.php?show=Bones&exact=1&ep=2x04
    base_URL = "http://services.tvrage.com/tools/quickinfo.php"
    show_str = "?show="+name
    options = "&exact=1"
    episode_str = "&ep=" + str(season) + "x" + str(episode)
    full_URL = base_URL + show_str + options + episode_str
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", full_URL)
    mvals = m.groupdict()
    if mvals['port'] is None:
        mvals['port'] = 80
    try:
        conn = httplib.HTTPConnection(mvals['host'],mvals['port'])
        conn.request('GET',mvals['path'],"");
        responce = conn.getresponse()
        fullhtmlpage = responce.read()
        conn.close()
    except Exception,e:
        log_to_file("get_espisode_info: Failed to retrieve show name using URL: " + full_URL)
        log_to_file("get_espisode_info: Exception was value: " + str(e))
        return "" , ""
        
    start_episode_info =  fullhtmlpage.find("Episode Info")
    sub_string1 = fullhtmlpage[start_episode_info:]
    start_episode_name = sub_string1.find("^")
    sub_string2 = sub_string1[start_episode_name+1:]
    end_episode_name = sub_string2.find("^")
    episode_name = sub_string1[start_episode_name+1:end_episode_name+start_episode_name+1]
    
    start_show_name =  fullhtmlpage.find("Show Name")
    sub_string1 = fullhtmlpage[start_show_name:]
    start_episode_name = sub_string1.find("@")
    sub_string2 = sub_string1[start_episode_name+1:]
    end_episode_name = sub_string2.find("\n")
    show_name = sub_string1[start_episode_name+1:end_episode_name+start_episode_name+1]
    return show_name, episode_name  

def is_tv_show(raw_name):
    raw_name = raw_name.replace(' ','.');
    raw_name = raw_name.lower()

    extract_SE = re.match(".*[sS]?(\\d{2})[eE]?(\\d{2}).*\.avi$", raw_name)
    if extract_SE is None:
        extract_SE = re.match(".*[sS]?(\\d{1})[eE]?(\\d{2}).*\.avi$", raw_name)
        if extract_SE is None:
            extract_SE = re.match(".*[sS]?(\\d{1})[eE]?(\\d{1}).*\.avi$", raw_name)
            if extract_SE is None:
                #This does not match a show
                return ""
    show_group = extract_SE.groups()
    extracted_season = int(show_group[0])
    extracted_episode = int(show_group[1])
    extracted_name = raw_name[:raw_name.find("s"+show_group[0])]
    extracted_name = extracted_name.replace('.',' ')
    extracted_name = extracted_name.rstrip()
    
    proper_show_name, proper_episode_name = get_espisode_info(extracted_name, extracted_season, extracted_episode)
    
    if len(proper_show_name) == 0 or len(proper_episode_name) == 0 :
        return ""
    
    proper_show_name += " S" + str(extracted_season).zfill(2)
    proper_show_name += " E" + str(extracted_episode).zfill(2)
    proper_show_name +=  " - " + proper_episode_name
    proper_show_name += raw_name[raw_name.rfind("."):]
    return proper_show_name

def format_movie(raw_name):
    raw_name = raw_name.lower()
    raw_name = raw_name.replace('.',' ')
    parts = raw_name.split(' ')
    #https://dl.vpnhub.ca/downloads/The.Super.2011.DvDScr.XviD.AC3-XtremE/The.Super.2011.DvDScr.XviD.AC3-XtremE.avi
    common_tags = [ '480p','720p','1080p','1080i',
                    'xvid','ac3','brrip','bdrip','bluray','dvdrip',
                    'cd','dvd','dvd9','r5','r4','r3','ts','cam','dvdscr',
                    'dvdscreener','vhsscreener','ppvrip','iflix',
                    'vision','ika','readnfo','XtremE']


    name = ""
    for part in parts:
        if part not in common_tags:
            name += part + " "
        else:
        #Once 1 tag is found stop
            break
    return name

def is_movie(raw_name):
    #http://www.imdbapi.com/?i=&t=The+Italian+Job+2003
    api_url = "http://www.imdbapi.com/?i=&t=" + format_movie(raw_name)
    api_url = api_url.replace(" ","%20")
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", api_url)
    mvals = m.groupdict()
    if mvals['port'] is None:
        mvals['port'] = 80
    fullhtmlpage = ""
    try:
        conn = httplib.HTTPConnection(mvals['host'],mvals['port'], timeout=10)
        conn.request('GET',mvals['path'],"");
        responce = conn.getresponse()
        fullhtmlpage = responce.read()
        conn.close()
    except Exception,e:
        log_to_file("get_espisode_info: Failed to retrieve show name using URL: " + api_url)
        log_to_file("get_espisode_info: Exception was value: " + str(e))
        return ""
    
    result = json.loads(fullhtmlpage)
    if result['Response'] == "Parse Error":
        return ""
    format =  result['Title'] + " (" + result['Year'] + ")"
    format += raw_name[raw_name.rfind("."):]
    return format





    
def fixEntriesAfter(fix_queue_id):
    for a_job in Job.objects.all().order_by('queue_id'):
        if a_job.queue_id > fix_queue_id:
            a_job.queue_id = a_job.queue_id -1
            a_job.save()
    
def deleteJobs(jobs):
    for a_job in jobs:
        a_job.delete()
        log_to_file("Removed job with queue id: "+str(a_job.queue_id))
    jobs.reverse()
    for a_job in jobs:
        fixEntriesAfter(a_job.queue_id)

def killJob(pid):
    if pid != -1:
        try:
            if sys.platform == "win32":
                PROCESS_TERMINATE = 1
                handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
            else:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            log_to_file("Process: "+str(pid)+" does not exsist")
            
def startJob(job):
    #required a_job.full_url,a_job.filename
    if job.autorename == True:
        pass
    '''if autoRename flag set:
                    filename = urllib.unquote(filename)
                show_name = is_tv_show(filename)
                if len(show_name) > 0:
                   filename = show_name
                else:
                    movie_name = is_movie(filename)
                    if len(movie_name) > 0:
                            filename = movie_name
                    else:
                        parent_dir = urllib.unquote(parent_dir)
                        movie_name = is_movie(parent_dir)
                        if len(movie_name) > 0:
                            filename = movie_name'''
    URL = job.full_url
    local_path = job.local_directory + job.filename
    log_to_file("Starting job: "+URL+" Saving to local path: "+local_path)
    #ARGS = [settings.BINARY_CURL,'-u',settings.USERNAME+':'+settings.PASSWORD,'-k','-C','-',URL,'-o',local_path]
    WGET_ARGS = ['wget','-c','-q','--user='+settings.USERNAME,'--password='+settings.PASSWORD,'--no-check-certificate',URL,'--output-document='+local_path]
    process = subprocess.Popen(WGET_ARGS,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return process.pid
    
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

    for a_job in Job.objects.all().order_by('queue_id'):
        if a_job.status.startswith('New'):
            log_to_file('new job found')
            if a_job.full_url.endswith('/'):
                #load directory
                loadDirectory(a_job)
                continue #continue, because this specific job is going to be deleted, and more created
            elif a_job.autorename:
                show_name = is_tv_show(a_job.filename)
                if len(show_name) > 0:
                   a_job.filename = show_name
                else:
                    movie_name = is_movie(a_job.filename)
                    if len(movie_name) > 0:
                            a_job.filename = movie_name
                    '''else:
                        parent_dir = urllib.unquote(parent_dir)
                        movie_name = is_movie(parent_dir)
                        if len(movie_name) > 0:
                            a_job.filename = movie_name'''
                a_job.autorename = False
                a_job.save()

            a_job.total_size = getContentLength(a_job.full_url)
            a_job.display_size = convert_bytes(a_job.total_size)
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
            if os.path.exists(a_job.local_directory + a_job.filename):
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
                a_job.eta = convert_time(ETA)
                a_job.save()
            else:
                log_to_file("Cannot find file: "+a_job.local_directory + a_job.filename+" to compute stats for")

        if a_job.progress ==100 and a_job.status !='Finished' and a_job.status != 'Deleting...' and a_job.status != 'Deleting With Data...':
            a_job.status = 'Finished'
            a_job.dl_speed=0
            a_job.process_pid=-1
            a_job.save()
        
        if a_job.status == 'Starting...':
            a_job.process_pid = startJob(a_job)
            a_job.status = "Running"
            a_job.save()
        
        elif a_job.status == 'Stopping...':
            killJob(a_job.process_pid)
            a_job.process_pid = -1
            a_job.dl_speed=0
            a_job.status="Stopped"
            a_job.eta = ""
            log_to_file("Stopped: "+str(a_job.queue_id)+" "+a_job.filename)
            a_job.save()
        
        elif a_job.status == 'Deleting...' or a_job.status == 'Deleting With Data...':
            killJob(a_job.process_pid)
            tobeDel.append(a_job)
            if a_job.status == 'Deleting With Data...':
                try:
                    os.remove(a_job.local_directory + a_job.filename)
                except OSError:
                    if a_job.dled_size != 0:
                        log_to_file("Could not remove data for file: " + a_job.local_directory + a_job.filename)
                    
        elif a_job.status == 'Running':
            num_dls = num_dls +1
        elif a_job.status == "Queued" and num_dls < num_dls_at_once:
            a_job.process_pid = startJob(a_job)
            a_job.status = "Running"
            a_job.save()
            num_dls = num_dls +1
    deleteJobs(tobeDel)

class Command(BaseCommand):
    args = '<poll_id poll_id ...>'
    help = 'Closes the specified poll for voting'
    def handle(self, *args, **options):
        print "Now running... View",settings.ENGINE_LOG,"for more information"
        while(1):
            #try:
            runEngine()
            time.sleep(1)
            #except Exception,e:
             #   log_to_file(str(e))
                
        
