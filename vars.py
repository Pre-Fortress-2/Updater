from platform import system
import os
from enum import Enum

# Debug flag.
DEBUG = True

# Server we're going to extract files from.
WEBSITE_URL = 'https://archive.prefortress.com/latest/'
# New PF2 download's file name
FILE_NAME = 'latest.tar.gz'
# latest file
FILE_URL = WEBSITE_URL + FILE_NAME

# Temp path.
TEMP_PATH = ''
if system() == 'Windows':
    TEMP_PATH = os.environ.get('TEMP') # Windows environmental variable for the temp folder.
elif system() == 'Linux':
    TEMP_PATH = '/var/tmp' # Temp folder in Linux

# Sourcemod path set by setup_game_path()
SOURCEMOD_PATH = ''
# Game path set by setup_game_path()
GAME_PATH = ''

# Versions in string form.
LOCAL_VERSION_STRING = ''
SERVER_VERSION_STRING = ''

# Update codes the check_for_update function will use to do the appropriate action
class UpdateCode( Enum ):
    UPDATE_NO = 0, # Game is up to date.
    UPDATE_YES = 1, # Game needs an update.
    UPDATE_INTERRUPTED = 2, # Game's update was interrupted somehow, restore
    UPDATE_GAME_NOT_INSTALLED = 3, # Game isn't installed