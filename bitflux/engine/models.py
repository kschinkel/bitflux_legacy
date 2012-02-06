from django.db import models, connection
from django.contrib.auth.models import User

class LockingManager(models.Manager):
    ''' Add lock/unlock functionality to manager.
    
    Example::
    
        class Job(models.Model):
        
            manager = LockingManager()
    
            counter = models.IntegerField(null=True, default=0)
    
            @staticmethod
            def do_atomic_update(job_id)
                #Updates job integer, keeping it below 5
                try:
                    # Ensure only one HTTP request can do this update at once.
                    Job.objects.lock()
                    
                    job = Job.object.get(id=job_id)
                    # If we don't lock the tables two simultanous
                    # requests might both increase the counter
                    # going over 5
                    if job.counter < 5:
                        job.counter += 1                                        
                        job.save()
                
                finally:
                    Job.objects.unlock()
     
    
    '''    

    def lock(self):
        ''' Lock table. 
        
        Locks the object model table so that atomic update is possible.
        Simulatenous database access request pend until the lock is unlock()'ed.
        
        Note: If you need to lock multiple tables, you need to do lock them
        all in one SQL clause and this function is not enough. To avoid
        dead lock, all tables must be locked in the same order.
        
        See http://dev.mysql.com/doc/refman/5.0/en/lock-tables.html
        '''
        cursor = connection.cursor()
        table = self.model._meta.db_table
        #logger.debug("Locking table %s" % table)
        cursor.execute("LOCK TABLES %s WRITE" % table)
        row = cursor.fetchone()
        return row
        
    def unlock(self):
        ''' Unlock the table. '''
        cursor = connection.cursor()
        table = self.model._meta.db_table
        cursor.execute("UNLOCK TABLES")
        row = cursor.fetchone()
        return row       
        
        
class Job(models.Model):
    objects = LockingManager()

    process_pid = models.IntegerField()
    queue_id = models.IntegerField()
    gid = models.IntegerField()
    dl_speed = models.IntegerField()
    time_seg_start = models.IntegerField()
    time_seg_end = models.IntegerField()
    display_size = models.CharField(max_length=512)
    total_size = models.FloatField()
    dled_size = models.FloatField()
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
