from django.http import HttpResponse
from django.core import serializers
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from bitflux.engine.models import Job
from bitflux.engine.models import UserProfile
from bitflux.engine.models import deamon
from bitflux.engine.models import autoDLer
from bitflux.engine.models import autoDLEntry
from bitflux.engine.models import log
from django.template import Context, loader
from django.core.files import File
from django.conf import settings
import threading,thread
import subprocess 
import httplib
import urllib
try:
    import json
except ImportError:
    import simplejson as json
import re
import time
import ctypes
import sys
import os
import shutil
from HTMLParser import HTMLParser
from datetime import datetime, timedelta

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

@login_required
def enginestatus(request):
    objList = []
    response = 'up'
    os.environ['TZ'] = 'US/Eastern'

    for engine in deamon.objects.all():
        if datetime.now() - engine.ts > timedelta (seconds=20):
            response = 'down'
            
    return HttpResponse(json.dumps(response))


@login_required
def autodlerstatus(request):
    objList = []
    response = 'up'
    os.environ['TZ'] = 'US/Eastern'

    for autoDL in autoDLer.objects.all():
        if datetime.now() - autoDL.ts > timedelta (seconds=20):
            response = 'down'

    return HttpResponse(json.dumps(response))    


@login_required
def removeautodl(request):
    remove_id = int(request.POST.get('id',-1))
    try:
        obj = autoDLEntry.objects.get(id=remove_id)
    except autoDLEntry.DoesNotExist:
        return HttpResponse(json.dumps("INVALID ID:"+str(remove_id)))
    for a_log in obj.logs.all():
        a_log.delete()
    obj.delete()
    return HttpResponse(json.dumps("OK"))

    
@login_required
def autoDLLog(request):
    autoDLid = int(request.GET.get('id',-1))
    try:
        a_entry = autoDLEntry.objects.get(id=autoDLid)
    except autoDLEntry.DoesNotExist:
        return HttpResponse(json.dumps("INVALID ID:"+str(autoDLid)))
    objList = []
    a_obj =  {'notes':a_entry.dl_dir,'ts':'-','season_num':a_entry.season_start_at,'episode_num':a_entry.ep_start_at}
    objList.append(a_obj)
    for a_log in a_entry.logs.all():
        a_obj =  {'notes':a_log.notes,'ts':str(a_log.ts),'season_num':a_log.season_num,'episode_num':a_log.episode_num}
        objList.append(a_obj)
    dataObj = { 'count' : len(objList), 'total': len(objList),'autoDLLogs': objList }
    return HttpResponse(json.dumps(dataObj),mimetype="application/json")


@login_required
def autodlnew(request):
    #response = 'NAME:' + request.POST.get('autoDL_name','none')+'|SEASON:'+request.POST.get('autoDL_season_start','none')+'|EPISODE:'+request.POST.get('autoDL_episode_start','none')
    name = request.POST.get('autoDL_name','none')
    ERROR= ""
    try:
        season_start = int(request.POST.get('autoDL_season_start','none'))
    except ValueError:
        ERROR += "INVALID Season start value! | "
        
    try:
        episode_start = int(request.POST.get('autoDL_episode_start','none'))
    except ValueError:
        ERROR += "INVALID Episode start value! | "
        
    if name == 'none':
        ERROR += "No Name Provided"
    if ERROR is not "":
        return HttpResponse(json.dumps(ERROR))
    entry = autoDLEntry()
    entry.name = name
    
    try:
        profile = request.user.get_profile()
    except:
        profile = UserProfile()
        profile.user = request.user
        profile.dl_dir = settings.LOCAL_DIR
        profile.save()

    entry.dl_dir = profile.dl_dir
    entry.season_start_at = season_start
    entry.ep_start_at = episode_start
    entry.save()
    
    os.environ['TZ'] = 'US/Eastern'
    
    new_log = log()
    new_log.notes = "Created"
    new_log.ts = datetime.now()
    new_log.season_num = 0
    new_log.episode_num = 0
    new_log.save()
    
    entry.logs.add(new_log)
    
    return HttpResponse(json.dumps("OK"))

    
@login_required
def myview(request):
    start = int(request.GET.get('start',0))
    limit = int(request.GET.get('limit',2))
    
    objList = []
    for a_job in Job.objects.all():
        display_dl_speed = convert_bytes(a_job.dl_speed)+'ps'
        '''name_list = a_job.filename.split("/")
        name = name_list[len(name_list)-1]'''
        a_obj =  {'filename':a_job.filename,
                    'total_size' : a_job.display_size,
                    'queue_id' : a_job.queue_id,
                    'status' : a_job.status,
                    'dl_speed' : display_dl_speed,
                    'progress' : a_job.progress,
                    'eta' : a_job.eta,
                    'pid' : a_job.process_pid,
                    'nid'  : a_job.id
                    }
        objList.append(a_obj)
        
    objList2 = objList
    end = start + limit
    if end > len(objList):
        end = len(objList)
    
    objList = objList[start:end]
    dataObj = { 'count' : len(objList), 'total': len(objList2),'downloads': objList }

    return HttpResponse(json.dumps(dataObj),mimetype="application/json")


@login_required
def index(request):
    if request.method == 'POST':
        if 'newDL' in request.POST:
            the_action ="";    
            if 'start' in request.POST:
                status = "New; Start"
                the_action = 'start'
            elif 'queue' in request.POST:
                the_action = 'queue'
                status = "New; Queue"
            elif 'pause' in request.POST:
                the_action = 'pause'
                status = "New; Stop"
            withAutoRename = request.POST.get("withAutoRename", "false")
            
            URL = request.POST.get("URL",None)
            URL = urllib.unquote(URL)
            m = re.match(r"(?P<type>[^:]+)://(?P<host>[^:/]+)(:(?P<port>\d+))?(?P<path>.*)", URL)
            mvals = m.groupdict()    
            full_dl_path = mvals['type']+'://' + mvals['host'] + urllib.quote(mvals['path'] )
            if withAutoRename == "true":
                autoRename = True
            else:
                autoRename = False
            
            if full_dl_path.endswith('/'):
                mod_url = mvals['path'].rstrip('/')
                OUT_list = mod_url.split('/')
                filename = OUT_list.pop()
            else:
                OUT_list = mvals['path'].split('/')
                filename = OUT_list.pop()
                
            try:
                profile = request.user.get_profile()
            except:
                profile = UserProfile()
                profile.user = request.user
                profile.dl_dir = settings.LOCAL_DIR
                profile.save()
            new_job = Job()
            new_job.autorename = autoRename
            filename = urllib.unquote(filename)
            size = 0
            new_job.queue_id = len(Job.objects.all())
            new_job.process_pid = -1
            new_job.dl_speed = 0
            new_job.gid = -1
            new_job.time_seg_start = time.time()
            new_job.time_seg_end = new_job.time_seg_start
            new_job.display_size = convert_bytes(size)
            new_job.total_size = size
            new_job.dled_size = 0
            new_job.full_url = full_dl_path
            new_job.local_directory = profile.dl_dir
            new_job.filename = filename
            new_job.notes = "CURL download: " + new_job.local_directory + new_job.filename
            new_job.progress = 0
            new_job.status = status
            new_job.eta = ""
            new_job.save()
            returnlist = ['Added entry',filename];
            return HttpResponse(Context( {'action_performed':the_action,'list':returnlist} ))
            
        elif 'up' in request.POST:
            nid = request.POST.get('up')   
            if int(nid) != 0:
                job1 = Job.objects.get(id=int(nid))
                prev_id = job1.queue_id
                job1.queue_id = job1.queue_id -1
                job2 = Job.objects.get(queue_id=prev_id-1)
                job2.queue_id = job2.queue_id +1
                job1.save()
                job2.save()
            
        elif 'down' in request.POST:
            nid = request.POST.get('down')
            selected = Job.objects.get(id=int(nid))
            down_id = selected.queue_id
            if int(down_id) != len(Job.objects.all())-1:
                job1 = Job.objects.get(queue_id=int(down_id))
                job1.queue_id = job1.queue_id +1
                job2 = Job.objects.get(queue_id=int(down_id)+1)
                job2.queue_id = job2.queue_id -1
                job1.save()
                job2.save()
        elif 'Action' in request.POST:
            returnlist = [];
            the_action ="";
            check_list_del = request.POST.getlist('delete')
            check_list_stop = request.POST.getlist('stop')
            check_list_start = request.POST.getlist('start')
            check_list_queue = request.POST.getlist('queue')
            
            
            for a_check in check_list_queue:
                a_job = Job.objects.get(id=int(a_check))
                a_job.status = "Queued"
                a_job.save()
            for a_check in check_list_stop:
                the_action="Stopped";
                a_job = Job.objects.get(id=int(a_check))
                returnlist.append(int(a_check))
                a_job.status = "Stopping...";
                a_job.save();        
            for a_check in check_list_del:
                a_job = Job.objects.get(id=int(a_check))
                if 'DelWData' in request.POST:
                    a_job.status="Deleting With Data..."
                    the_action="Deleted With Data";
                else:
                    a_job.status="Deleting..."
                    the_action="Deleted";
                returnlist.append(int(a_check))
                a_job.save()
            for a_check in check_list_start:
                the_action="Started";
                a_job = Job.objects.get(id=int(a_check))
                a_job.status = "Starting..."
                a_job.save()
                returnlist.append(int(a_check))
            if 'cleanup' in request.POST:
                the_action="Cleaned Up";
                for a_job in Job.objects.all():
                    if a_job.status == 'Finished':
                        a_job.status = 'Deleting...'
                        a_job.save()
                        returnlist.append(a_job.id)
            return HttpResponse(Context( {'action_performed':the_action,'list':returnlist} ))
        #return HttpResponse(Context( {'status':'Nothing was done'} ))
            
    job_list = Job.objects.all()
    t = loader.get_template('index.html')
    c = Context( { 'job_list':job_list })
    #print "DONE"
    return HttpResponse(t.render(c))
    #return HttpResponse('test')
    #return render_to_response('index.html')


@login_required
def newdir(request):
    dir = request.POST.get('mkDir')
    if dir is not None and dir !='':
        full_dir = request.user.get_profile().dl_dir +dir
        try:
            os.mkdir(full_dir)
            value = 'Created DIR: '+ full_dir
        except OSError:
            value = 'Failed to create DIR: '+ full_dir
            pass
        
    else:
        value = 'Invalid DIR!'
    return HttpResponse(json.dumps(value),mimetype="application/json")

@login_required
def removeEntry(request):
    entry = request.POST.get('rmEntry')
    entry = settings.LOCAL_DIR.rstrip('/') + entry
    if dir is not None and dir !='':
        try:
            os.remove(entry)
        except OSError:
            try:
                shutil.rmtree(entry)
            except OSError:
                return HttpResponse(json.dumps("Unable to remove entry: " + entry),mimetype="application/json")
        value = 'Removed Entry: ' + entry
    else:
        value = 'Invalid Entry name'
    return HttpResponse(json.dumps(value),mimetype="application/json")
    
@login_required
def listAutoDLs(request):
    objList = []
    for entry in autoDLEntry.objects.all():
        latest_log = None
        for a_log in entry.logs.all():
            if latest_log is None:
                latest_log = a_log
            elif a_log.ts > latest_log.ts:
                latest_log = a_log
        #a_obj =  {'id':entry.id,'entryName':entry.name,'season_start':entry.season_start_at,'episode_start':entry.ep_start_at}
        a_obj =  {'id':entry.id,'entryName':entry.name,'latest_season':latest_log.season_num,'latest_episode':latest_log.episode_num}
        
        objList.append(a_obj)

    dataObj = { 'count' : len(objList), 'total': len(objList),'autoDLList': objList }
    return HttpResponse(json.dumps(dataObj),mimetype="application/json")

@login_required
def getCWD(request):
    try:
        profile = request.user.get_profile()
    except:
        profile = UserProfile()
        profile.user = request.user
        profile.dl_dir = settings.LOCAL_DIR
        profile.save()
    
    dir = profile.dl_dir.replace(settings.LOCAL_DIR,'')
    if len(dir) == 0:
        dir = "/"
    return HttpResponse(json.dumps(dir))
    
@login_required
def download(request):
    path = request.GET.get('downloadpath')
    path = settings.LOCAL_DIR + path
    file_list = path.split('/')
    filename = file_list.pop();
    response = HttpResponse(open(path))
    response['Content-Disposition'] = 'attachment; filename='+filename
    response['Content-Length'] = os.path.getsize(path)
    return response
    
@login_required
def listDirContents(request):
    objList = []
    currentDir = request.GET.get('currentDir')
    '''try:
        profile = request.user.get_profile()
    except:
        profile = UserProfile()
        profile.user = request.user
        profile.dl_dir = settings.LOCAL_DIR
        profile.save()
    
    if currentDir is not None:
        #if currentDir != '/' or profile.dl_dir != '/':
        profile.dl_dir = settings.LOCAL_DIR + currentDir.lstrip('/')
        profile.save()'''
    
    '''if profile.dl_dir != settings.LOCAL_DIR:
        a_obj =  {'entryName':profile.dl_dir.replace(settings.LOCAL_DIR,''),
            'isDir' : 'P',
            'size' : '-',
            'date' : '-',
            }
        objList.append(a_obj)'''
    new_CWD = currentDir.lstrip('/')
    dir_to_list = settings.LOCAL_DIR + new_CWD
    '''try:
        os.listdir(dir_to_list)
    except OSError:
        profile.dl_dir = settings.LOCAL_DIR
        profile.save()'''
    for entryName in os.listdir(dir_to_list):
        if str(entryName).startswith('.'):
            continue
        isDir = 'N'
        if os.path.isdir(dir_to_list+"/"+entryName):
            isDir = 'Y'
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(dir_to_list+"/"+entryName)
        if isDir == 'Y':
            dSize = '-'
        else:
            dSize = convert_bytes(size)
        a_obj =  {'entryName':entryName,
                    'isDir' : isDir,
                    'size' : dSize,
                    'date' : time.ctime(ctime),
                    }
        objList.append(a_obj)

    dataObj = { 'count' : len(objList), 'total': len(objList),'dirList': objList }
    
    #Save CWD
    try:
        profile = request.user.get_profile()
    except:
        profile = UserProfile()
        profile.user = request.user
        profile.dl_dir = settings.LOCAL_DIR
        
    profile.dl_dir = settings.LOCAL_DIR + currentDir
    profile.save()
    
    return HttpResponse(json.dumps(dataObj),mimetype="application/json")


    