from platform import system
import os

# Debug flag.
DEBUG = True

# Server we're going to extract files from.
WEBSITE_URL = 'https://archive.prefortress.com/latest/'
# latest file
FILE_URL = WEBSITE_URL + 'latest.tar.gz'

# Temp path.
TEMP_PATH = ''
if system() == 'Windows':
    TEMP_PATH = os.environ.get('TEMP') # Windows environmental variable for the temp folder.
elif system() == 'Linux':
    TEMP_PATH = '/var/tmp' # Temp folder in Linux

# Sourcemod path set by setup_sourcemod_path()
SOURCEMOD_PATH = ''
# Local build on computer
LOCAL_VERSION = 0
# Latest build on server
SERVER_VERSION = 0