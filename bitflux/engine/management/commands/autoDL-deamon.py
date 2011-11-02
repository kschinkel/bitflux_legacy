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
import urllib2
import smtplib
import xmlrpclib


def log_to_file(msg):
    f = open(settings.AUTODL_LOG, 'a')
    f.write(str(datetime.now())+": "+msg+"\n")
    f.close
    
def matchWithShows(entry_name_from_server):
    entry_name_from_server = entry_name_from_server.lower()
    debug = False
    for a_show in autoDLEntry.objects.all():
        if debug:
            print 'autodl entry',a_show
        a_show_name = a_show.name.replace(' ','.');
        a_show_name = a_show_name.lower()
        extract_SE = re.match(".*("+a_show_name+").*?[sS]?(\\d{2})[eE]?(\\d{2}).*\.", entry_name_from_server)
        if extract_SE is None:
            if debug:
                print entry_name_from_server, "did not match",a_show_name
            extract_SE = re.match(".*?("+a_show_name+").*?[sS]?(\\d{1})[eE]?(\\d{2}).*\.", entry_name_from_server)
            if extract_SE is None:
                if debug:
                    print entry_name_from_server, "did not match",a_show_name
                extract_SE = re.match(".*?("+a_show_name+").*?[sS]?(\\d{1})[eE]?(\\d{1}).*\.", entry_name_from_server)
                if extract_SE is None:
                    if debug:
                        print entry_name_from_server, "did not match",a_show_name
                    #This does not match this show
                    continue         
        #If reached this part it has matched 'a_show' to the 'name'
        if debug:
            print entry_name_from_server,'matched!'
        show_group = extract_SE.groups()
        season_found = int(show_group[1])
        episode_found = int(show_group[2])
        return True, season_found, episode_found, a_show
    if debug:
        print entry_name_from_server, "did not match any autoDL entries"
    return False, -1, -1, None
    
def email_notification(dl_name,email_address):
    fromaddr = settings.EMAIL_FROM_ADDR
    toaddrs  =  email_address
    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n"
           % (fromaddr, toaddrs,"Bitflux Notification"))

    msg = msg + "~BitFlux~ is notifying you of a new automatic download: "+dl_name

    server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(settings.EMAIL_FROM_ADDR, settings.EMAIL_FROM_PASSWD)
    #server.set_debuglevel(1)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
    log_to_file("Email notification sent to: "+email_address+" for DL: "+dl_name)
    
def newDLtoAdd(url, found_id, filename,found_season,found_episode,dl_dir,size):
    #out = dl_dir + filename
    try:
        filename = unicode(filename, errors='ignore')
    except TypeError:   #if type error occurs, just pass, use filename untouched
        pass
    #Create the new Job
    new_job = Job()
    new_job.status = 'Queued'
    new_job.queue_id = len(Job.objects.all())
    new_job.process_pid = -1
    new_job.gid = -1
    new_job.dl_speed = 0
    new_job.time_seg_start = -1
    new_job.time_seg_end = -1
    new_job.display_size = common.convert_bytes(size)
    new_job.total_size = size
    new_job.dled_size = 0
    new_job.full_url = url
    new_job.local_directory = dl_dir
    new_job.filename = common.name_wrapper(filename)
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
    
def search_server_feed(full_torrent_listing):
    for entry in full_torrent_listing:
        if entry[1] == 0:   #there are no bytes remaining for the download
            filename = entry[2]
            is_match, season_found, episode_found, a_show = matchWithShows(filename)
            if is_match:
                a_show_name = a_show.name.replace(' ','.');
                a_show_name = a_show_name.lower()
                if season_found >= a_show.season_start_at and episode_found >= a_show.ep_start_at: #it is a season and episode we want
                    if check_show_logs(a_show,season_found,episode_found) == False: #make sure we have not already DLed it
                        count = 0
                        URLS = []
                        size = -1
                        while True: 
                            a_entry_url = settings.RUTORRNET_URL + "/plugins/data/action.php?hash=" + entry[0] + "&no=" + str(count)
                            status, filename, size = common.getEntryInfo(a_entry_url)
                            type = filename[filename.rfind("."):]
                            type = type.strip(".")
                            URLS.append({"URL":a_entry_url,'size':size,'type':type})
                            if status:
                                count += 1
                            else:
                                break;
                        if count == 1:
                            file_type_wanted = False 
                            for a_extension in settings.EXTENSIONS:
                                if URLS[0]["type"] == a_extension:
                                    file_type_wanted = True
                            if file_type_wanted:
                                proper_show_name, proper_episode_name = common.get_espisode_info(a_show_name, season_found, episode_found)
                                if len(proper_show_name) == 0:
                                    #print "Show name could not be retrieved"
                                    tv_show_rename = a_show_name
                                else:
                                     tv_show_rename = proper_show_name      
                                        
                                tv_show_rename += " S" + str(season_found).zfill(2)
                                tv_show_rename += " E" + str(episode_found).zfill(2)
                                
                                if len(proper_episode_name) != 0:
                                    tv_show_rename +=  " - " + proper_episode_name
                                
                                tv_show_rename += "." + URLS[0]["type"]
                                log_to_file("Found Show to DL: "+tv_show_rename)
                                #
                                #There has been a failure after this point, seems to be when the TV show is not named properly
                                #
                                newDLtoAdd(URLS[0]["URL"],a_show.id,tv_show_rename, season_found ,episode_found, a_show.dl_dir,URLS[0]["size"])
                                #send email notifications
                                for email_addr in settings.EMAIL_TO_LIST:
                                    #send email notifications
                                    email_notification(tv_show_rename, email_addr)
                            
                        elif count > 1:
                            # do nothing right now
                            #TBD
                            pass

                        '''print"============================================"
                        print "start dl with: ", a_entry_url
                        print "name:", filename
                        print "size:", size
                        print "S",season,"E",episode'''
                    

    
def dl_server_feed():
    #log_to_file('Requesting list from server...')
    try:
        URL = settings.RUTORRNET_URL + "/plugins/rpc/rpc.php"
        add_name_pass = settings.USERNAME + ":" + settings.PASSWORD + "@"
        URL = URL.replace("://","://"+add_name_pass)
        proxy = xmlrpclib.ServerProxy(URL)
        result = proxy.d.multicall("main","d.get_hash=","d.get_left_bytes=","d.get_name=","d.get_base_path=")
    except Exception,e:
        log_to_file("Failed to retrieve page from server: "+str(e))
        return
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
            if datetime.now() - prev_time > timedelta (seconds=settings.AUTODL_POLL_INTERVAL):
                dl_server_feed()
                prev_time = datetime.now()
