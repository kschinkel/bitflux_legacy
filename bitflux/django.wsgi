import os
import sys
sys.path.append('/var/www/bitflux')


os.environ['DJANGO_SETTINGS_MODULE'] = 'bitflux.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
