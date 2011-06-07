from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	(r'^admin/', include(admin.site.urls)),
    (r'^/?$', 'bitflux.engine.views.index'),
    (r'^myview/$', 'bitflux.engine.views.myview'),
	(r'^autoDLList/', 'bitflux.engine.views.listAutoDLs'),
	(r'^dirList/', 'bitflux.engine.views.listDirContents'),
	(r'^enginestatus/$', 'bitflux.engine.views.enginestatus'),
	(r'^autodlerstatus/$', 'bitflux.engine.views.autodlerstatus'),
	(r'^autodlnew/$', 'bitflux.engine.views.autodlnew'),
	(r'^autoDLLog/$', 'bitflux.engine.views.autoDLLog'),
	(r'^removeautodl/$', 'bitflux.engine.views.removeautodl'),
    (r'^getCWD/$', 'bitflux.engine.views.getCWD'),
	(r'^newdir/$', 'bitflux.engine.views.newdir'),
    (r'^rmEntry/$', 'bitflux.engine.views.removeEntry'),
    (r'^download/$', 'bitflux.engine.views.download'),
	#(r'^newDL/myview/?$', 'bitflux.engine.views.myview'),
	#(r'^newDL/', 'bitflux.engine.views.newDL'),
	(r'^accounts/login/$', "django.contrib.auth.views.login", 
	{"template_name": "login.html"}),
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
    {'document_root': settings.BASE_DIR + 'media'}),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
    {'document_root': settings.BASE_DIR + 'media/admin_media'})
)
