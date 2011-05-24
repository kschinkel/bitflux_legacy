from django.db import models
from django.contrib.auth.models import User

class Job(models.Model):
    process_pid = models.IntegerField()
    queue_id = models.IntegerField()
    gid = models.IntegerField()
    dl_speed = models.IntegerField()
    time_seg_start = models.IntegerField()
    time_seg_end = models.IntegerField()
    display_size = models.CharField(max_length=512)
    total_size = models.IntegerField()
    dled_size = models.IntegerField()
    #dled_dif_size = models.IntegerField()    #Possibly not needed
    full_url = models.CharField(max_length=512)
    local_directory = models.CharField(max_length=512)
    filename = models.CharField(max_length=512)
    notes = models.CharField(max_length=200)
    status = models.CharField(max_length=200)
    progress = models.IntegerField()
    eta = models.CharField(max_length=200)
    autorename = models.BooleanField(default = False)
    def __unicode__(self):
        return self.notes + "--" + str(self.process_pid)
    #def delete(self, *args, **kwargs):
    #    super(Job,self).delete()
    
class deamon(models.Model):
    process_pid = models.IntegerField()
    ts = models.DateTimeField()

class autoDLer(models.Model):
    process_pid = models.IntegerField()
    ts = models.DateTimeField()    

    
class log(models.Model):
    notes = models.TextField()
    ts = models.DateTimeField()    
    season_num = models.IntegerField()
    episode_num = models.IntegerField()
    def __unicode__(self):
        return str(self.ts) +' : ' +self.notes + '- S' + str(self.season_num) + ' E' + str(self.episode_num)
        
class autoDLEntry(models.Model):
    name = models.TextField()
    season_start_at = models.IntegerField()
    ep_start_at = models.IntegerField()
    dl_dir = models.TextField()
    logs = models.ManyToManyField(log)
    def __unicode__(self):
        return self.name
        
class UserProfile(models.Model):
    user = models.ForeignKey(User, unique=True)
    dl_dir = models.TextField()
    def __unicode__(self):
        return self.dl_dir

User.profile = property(lambda u: UserProfile.objects.get_or_create(user=u)[0])
