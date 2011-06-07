#############################################
# Django settings for BitFlux project.
#############################################
LOCAL_DIR = '/mnt/Data/'                                            #Local directory for the filemanager
BASE_DIR = '/var/www/bitflux/'                                      #Base directory of bitflux; the full path of the directory which contains all files
USERNAME="someuser"                                                 #Username for third party server
PASSWORD="somepassword"                                             #Password for third party server
ENGINE_LOG = 'engine.log'                                           #log filename for the engine deamon
AUTODL_LOG = 'autoDL.log'                                           #log filename for the auto-downloader deamon
RUTORRNET_URL = 'http://adomain.com/rutorrent'                      #full URL of the ruTorrent interface
AUTODL_POLL_INTERVAL = 10                                           #number of seconds at which the auto downloader will poll the server
EXTENSIONS = ['avi']                                                #list of file extensions to look for. Used by the auto downloader
#Email notification settings
EMAIL_TO_LIST = {'someone@places.com','person2@places.com'}         #List of email addresses to send auto-downloaded items a notification to
EMAIL_FROM_ADDR = 'address@places.com'                              #Email address of where to send the notifications from
EMAIL_FROM_PASSWD = 'password'                                      #Password of the email address of where to send the notifications from
SMTP_SERVER = 'smtp.gmail.com'                                      #Name of SMTP server to use for sending email notifications
SMTP_PORT = 587                                                     #Port of SMTP server to use for sending email notifications


#############################################
#General Django settings
#############################################
AUTH_PROFILE_MODULE = 'engine.UserProfile'
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = '/var/www/bitflux/bitflux.db'             # Or path to database file if using sqlite3. 
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '9jb*9^xrlfx8+u@vl7q1%tzu)kx$b6d4$4i$l4l@2h6z2b=ma3'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'bitflux.disable.DisableCSRF', 
)

ROOT_URLCONF = 'bitflux.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    '/var/www/bitflux/templates/'
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'bitflux.engine',
    'django.contrib.admin',
)
