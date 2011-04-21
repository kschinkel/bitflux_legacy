from django.core.management.base import BaseCommand, CommandError
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import Job
from bitflux.engine.models import UserProfile
from bitflux.engine.models import deamon
from bitflux.engine.models import autoDLer
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import log
from django.conf import settings

import urllib2
import sys
import re
import base64
import httplib
import os
import time
from datetime import datetime, timedelta
from urlparse import urlparse
from sqlite3 import dbapi2 as sqlite
try:
    import json
except ImportError:
    import simplejson as json
from HTMLParser import HTMLParser
import urllib
import smtplib

def log_to_file(msg):
    f = open(settings.AUTODL_LOG, 'a')
    f.write(str(datetime.now())+": "+msg+"\n")
    f.close

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
        print "get_espisode_info: Failed to retrieve show name using URL: " + full_URL
        print "get_espisode_info: Exception was vale: " + str(e)
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
    
    
def email_notification(dl_name,email_address):
    fromaddr = settings.EMAIL_FROM_ADDR
    toaddrs  =  email_address
    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n"
           % (fromaddr, toaddrs,"Bitflux Notification"))

    msg = msg + "~BitFlux~ is notifying you of a new automatic download: "+dl_name

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(settings.EMAIL_FROM_ADDR, settings.EMAIL_FROM_PASSWD)
    #server.set_debuglevel(1)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
    log_to_file("Email notification sent to: "+email_address+" for DL: "+dl_name)

def convert_bytes(bytes):
    bytes = float(bytes)
    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fT' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fG' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fM' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fK' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size

def getContentLength(URL):
    m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", URL)
    mvals = m.groupdict()
    if mvals['port'] is None:
        mvals['port'] = 443

    OUT_list = mvals['path'].split('/')
    filename = OUT_list.pop()
    filename = urllib.unquote(filename)
    basic_auth = settings.USERNAME + ":"+settings.PASSWORD
    encoded = basic_auth.encode("base64")[:-1]
    headers = {"Authorization":"Basic %s" % encoded}
    params = ""
    conn = httplib.HTTPSConnection(mvals['host'],mvals['port'])
    conn.request('GET',mvals['path'],params,headers);
    responce = conn.getresponse()
    size = responce.getheader("content-length")
    conn.close()
    return size,filename
    
def newDLtoAdd(url, found_id, filename,found_season,found_episode,dl_dir):
    size, notused = getContentLength(url)
    #out = dl_dir + filename
    
    #Create the new Job
    new_job = Job()
    new_job.status = 'Queued'
    new_job.queue_id = len(Job.objects.all())
    new_job.process_pid = -1
    new_job.dl_speed = 0
    new_job.time_seg_start = -1
    new_job.time_seg_end = -1
    new_job.display_size = convert_bytes(size)
    new_job.total_size = size
    new_job.dled_size = 0
    #new_job.dled_dif_size = 0; removed
    new_job.full_url = url
    new_job.local_directory = dl_dir
    new_job.filename = filename
    new_job.notes = "Auto DLed:  " + new_job.local_directory + new_job.filename
    new_job.progress = 0;
    new_job.eta = ""
    new_job.save()
    
    #Create the new Log
    new_log = log()
    new_log.notes = 'Auto DLed'
    new_log.ts = datetime.now()
    new_log.season_num = int(found_season)
    new_log.episode_num = int(found_episode)
    new_log.save()
    
    #link the log to the autoDLEntry
    tobe_updated = autoDLEntry.objects.get(id=found_id)
    tobe_updated.logs.add(new_log)
    
def check_show_logs(show,S,E):
    for entry in show.logs.all():
        if S == entry.season_num and E == entry.episode_num:
            return True
    return False
    
def search_server_feed(data):
    for entry in data['torrents']:
        if entry['progress'] == 100: #we only want ones that are finished DLing on the server
            entry_name_from_server = entry['name']
            for a_show in autoDLEntry.objects.all():
                a_show_name = a_show.name.replace(' ','.');
                a_show_name = a_show_name.lower()
                entry_name_from_server = entry_name_from_server.lower()
                '''is_match = re.match("(.*?)"+a_show_name+"(.*?)\.avi$", entry_name_from_server)
                if is_match is None:
                    continue'''
                #log_to_file("Matched show name: "+entry_name_from_server+", Checking S and E...")
                #extract_SE = re.match("(.*?)[.\\s][sS]?(\\d{2})[eE]?(\\d{2}).*\.avi$", entry_name_from_server)
                extract_SE = re.match(".*("+a_show_name+").*?[sS]?(\\d{2})[eE]?(\\d{2}).*\.avi$", entry_name_from_server)
                if extract_SE is None:
                    extract_SE = re.match(".*?("+a_show_name+").*?[sS]?(\\d{1})[eE]?(\\d{2}).*\.avi$", entry_name_from_server)
                    if extract_SE is None:
                        extract_SE = re.match(".*?("+a_show_name+").*?[sS]?(\\d{1})[eE]?(\\d{1}).*\.avi$", entry_name_from_server)
                        if extract_SE is None:
                            #This does not match this show
                            continue
                #If reached this part it has matched 'a_show' to the 'name'
                show_group = extract_SE.groups()
                season_found = int(show_group[1])
                episode_found = int(show_group[2])
                if season_found >= a_show.season_start_at and episode_found >= a_show.ep_start_at: #it is a season and episode we want
                    if check_show_logs(a_show,season_found,episode_found) == False: #make sure we have not already DLed it
                        #only download stuff in the ROOT right now. If its in a sub folder there could be multiple files
                        if entry['path'] == '/':
                            url_to_dl = 'https://dl.vpnhub.ca/downloads/'+entry['name']
                            
                            proper_show_name, proper_episode_name = get_espisode_info(a_show_name, season_found, episode_found)

                            if len(proper_show_name) == 0:
                                print "Show name could not be retrieved"
                                tv_show_rename = show_name
                            else:
                                tv_show_rename = proper_show_name

                            tv_show_rename += " S" + str(season_found).zfill(2)
                            tv_show_rename += " E" + str(episode_found).zfill(2)

                            if len(proper_episode_name) == 0:
                                print "Episode name could not be retrieved"
                            else:
                                tv_show_rename +=  " - " + proper_episode_name
                            get_file_type = entry['name']
                            tv_show_rename += get_file_type[get_file_type.rfind("."):]
                            log_to_file("Found Show to DL: "+tv_show_rename)
                            newDLtoAdd(url_to_dl,a_show.id,tv_show_rename, season_found ,episode_found, a_show.dl_dir)
                            #send email notifications
                            for email_addr in settings.EMAIL_TO_LIST:
                                #send email notifications
                                email_notification(tv_show_rename, email_addr)
        
def dl_server_feed_OLD(URL): #No longer used
    #log_to_file('Requesting list from server...')
    try:
        req = urllib2.Request(URL)
        base64string = base64.encodestring(
                        '%s:%s' % (settings.USERNAME, settings.PASSWORD))[:-1]
        authheader =  "Basic %s" % base64string
        req.add_header("Authorization", authheader)
        handle = urllib2.urlopen(req)
        thepage = handle.read()
        result = json.loads(thepage) #parse the json page
    except Exception,e:
        log_to_file("Failed to retrieve page from server: "+str(e))
        return
    handle.fp._sock.recv=None # hacky avoidance
    handle.close()

    #log_to_file('Recived list of downloads form engine...')
    search_server_feed(result)
    
def dl_server_feed(URL):
    #log_to_file('Requesting list from server...')
    try:
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
        thepage = conn.getresponse().read()
        result = json.loads(thepage) #parse the json page
    except Exception,e:
        log_to_file("Failed to retrieve page from server: "+str(e))
        return
    conn.close()

    #log_to_file('Recived list of downloads form engine...')
    search_server_feed(result)

class Command(BaseCommand):
    args = '<poll_id poll_id ...>'
    help = 'Closes the specified poll for voting'    
    def handle(self, *args, **options):
        print "Now running... View",settings.AUTODL_LOG,"for more information"
        prev_time = datetime.now()
        while(1):
            time.sleep(1)
            for cleanup in autoDLer.objects.all():
                cleanup.delete()
            os.environ['TZ'] = 'US/Eastern'
            autoDLStatus = autoDLer()
            autoDLStatus.process_pid = os.getpid()
            autoDLStatus.ts = datetime.now()
            autoDLStatus.save()
            if datetime.now() - prev_time > timedelta (seconds=10):
                dl_server_feed(settings.SERVER_JSON_URL)
                prev_time = datetime.now()