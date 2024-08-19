'''
Proof of concept on how an updater could work. Linux and Windows compatible.
'''
import os
from platform import system
from tqdm import tqdm
import requests
import tarfile
import vpk # we need to determine the version file from the VPK
if system() == 'Windows':
    import winreg
    import userpaths # Get the downloads folder on windows 
import unidiff
from shutil import copy2, rmtree, copytree
from enum import Enum

import message

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

# Sourcemod path
SOURCEMOD_PATH = ''
# Local build on computer
LOCAL_VERSION = 0
# Latest build on server
SERVER_VERSION = 0

# update code.
class UpdateCode( Enum ):
    NO_UPDATE = 0,
    NEEDS_UPDATE = 1,
    NEEDS_UPDATE_INTERRUPTED = 2,
    PROMPT_DOWNLOAD = 3,


def setupsourcemodpath() -> None:
    '''
    Sets up the SOURCEMOD_PATH global variable. Stolen from TF2CDownloader.
    '''
    global SOURCEMOD_PATH
    if system() == 'Windows':
        try:
            REGISTRY = 0
            REGISTRY_KEY = ''
            if REGISTRY == 0:
                # Go to the Windows registry.
                REGISTRY = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                # Then try to find the Steam registry folder.
                REGISTRY_KEY = winreg.OpenKeyEx(REGISTRY, r'SOFTWARE\Valve\Steam', access=winreg.KEY_ALL_ACCESS)
            # If we have the registry key, look for the value 'SourceModInstallPath'
            value = winreg.QueryValueEx(REGISTRY_KEY, 'SourceModInstallPath')
            # Set the global variable.
            SOURCEMOD_PATH = value[0]
        except Exception as error:
            # Exception, print something here
            print( "Exception occurred: ", error )
    else: # Linux. We don't have a registry, so Steam has a "fake" one via registry.vdf
        try:
            sourcepath = None
            # Open the registry.vdf file, which holds a "fake" registry for Steam
            with open(os.path.expanduser(r'~/.steam/registry.vdf'), encoding="utf-8") as file:
                # Look for SourceModInstallPath.
                for _, line in enumerate(file):
                    if 'SourceModInstallPath' in line:
                        # If we find it, replace the paths with proper slashes for UNIX systems
                        sourcepath = line[line.index('/home'):-1].replace(r'\\', '/').replace('\"', '')
                        break
                # Close the file. We're done here.
                file.close()
            # Set the global variable.
            SOURCEMOD_PATH = sourcepath

        except Exception as error:
            # Exception, print something here
            print( "Exception occurred: ", error )


def check_for_update() -> int:
    '''
    Check if we need an update.
    returns UpdateCode.NO_UPDATE if we don't need an update, 
    returns UpdateCode.NEEDS_UPDATE if we do
    returns UpdateCode.NEEDS_UPDATE_INTERRUPTED if we were in the middle of an update 
    but was cancelled due to an error or was closed out prematurely
    returns UpdateCode.PROMPT_DOWNLOAD if we don't have the game installed
    '''
    # Traverse to the PF2 path
    sourcemod_path = os.path.join( SOURCEMOD_PATH, 'pf2' )

    # Get these global variables
    global LOCAL_VERSION
    global SERVER_VERSION

    # Do we have PF2 installed? If not, prompt a download.
    if not os.path.exists( sourcemod_path ):
        return UpdateCode.PROMPT_DOWNLOAD
     
    # Open the vpk file to get the version.txt file.
    # Note: pre-0.7.4 builds store it in the vpks
    try:
        # VPK path for the version.
        vpkpath = os.path.join( sourcemod_path, "pf2_misc_dir.vpk" )
        # Open the vpk file housing the version.txt
        vpkfile = vpk.open( vpkpath )
        # Get the file.
        file = vpkfile.get_file( 'version.txt' )
        # Get the version string from the file and convert it into an integer
        # Read the file, decode the file, format it as unicode, partition the important number part
        # and remove the periods from the version so that we can store the number
        LOCAL_VERSION = int( file.read().decode().format('utf-8').partition('=')[2].replace( '.', '' ) )
        # close the file
        file.close()
    except FileNotFoundError:
        print ('Could not find version.txt inside the VPK. Assuming this is a post-0.7.3 build.')
        # Note: post-0.7.3 build
        # try to open it if it's a normal file 
        try:
            # Get the version.txt file
            normpath = os.path.join( sourcemod_path, 'version.txt' )
            # Open the file.
            file = open( normpath )
            # convert this version text to a number.
            LOCAL_VERSION = int( file.read().partition('=')[2].replace( '.', '' ) )
            # close the file.
            file.close()
        except Exception as error:
            print ( "Exception occurred: ", error )

    except Exception as error:
        print ( "Exception occurred: ", error )

    # try to match that version.txt file from the server
    try:
        # Request version.txt from the website
        response = requests.get( WEBSITE_URL + 'version.txt' )
        # Get the text from it and strip new lines from it.
        SERVER_VERSION = int( response.text.strip('\n').replace( '.', '' ) )
        # Is our local version less than the one off the website?
        if LOCAL_VERSION < SERVER_VERSION:
            return UpdateCode.NEEDS_UPDATE # We need to update!!!
    except Exception as error:
        print( 'Exception occurred: ', error )

    # Check for an update file. If we have one, continue updating the game
    if os.path.exists( os.path.join( sourcemod_path, 'update_file' ) ):
        print( 'Continuing your update...\n' )
        return UpdateCode.NEEDS_UPDATE_INTERRUPTED

    return UpdateCode.NO_UPDATE # We don't need to update.


def download() -> bool: 
    '''
    Downloads the update, True if we downloaded it correctly, False if we didn't
    '''
    global FILE_URL
    try:
        # If this file already exists, delete it
        if os.path.exists( os.path.join( TEMP_PATH, 'latest.tar.gz' ) ):
            os.remove( os.path.join( TEMP_PATH, 'latest.tar.gz' ) )
    
        # Try requesting the server to get a file.
        response = requests.get( FILE_URL, stream=True, timeout=10 )

        total_size = int( response.headers.get( 'content-length', 0 ) )
        # show a progress bar to the console using tqdm.
        with open( os.path.join( TEMP_PATH, 'latest.tar.gz' ), "wb" ) as handle, tqdm( 
                                                                                desc='Downloading latest_tar.gz', 
                                                                                total=total_size,
                                                                                unit='iB',
                                                                                unit_scale=True ) as bar:
            # Write to the disk.
            for chunk in response.iter_content( chunk_size=16*1024 ):
                size = handle.write(chunk)
                bar.update(size)
                
    # did we time out? Did the server just not have it? etc...
    except Exception as error:
        print( 'An exception occurred: ', error )

    # Did we succeed?
    return response.status_code == 200


def extract() -> bool:
    '''
    Extracts the tar file into a new folder.
    '''
    print('Extracting the game...')
    # Flag to indicate success.
    success = False
    try:
        # Open the tar file that we just downloaded.
        with tarfile.open( os.path.join( TEMP_PATH, 'latest.tar.gz' ) ) as file:
            # Try extracting it
            file.extractall( os.path.join( TEMP_PATH, 'pf2_new' ) )
            # If we extracted it, set the flag for success.
            success = True
    except FileNotFoundError:
        # If we didn't find the file, stop
        print('Unable to open the file! Please try running this program again.')
    except tarfile.ExtractError:
        # If we're unable to extract the file, stop
        print( 'Unable to extract the file. Please try running this program again.' )
    except Exception as error:
        print( 'An exception occurred: ', error )
        
    # Remove this file immediately, we're done with it.
    if success:
        os.remove( os.path.join( TEMP_PATH, 'latest.tar.gz' ) )

    return success


def update() -> bool:
    '''
    Try to update the game with the downloaded build 
    via a diff file downloaded from the server.
    This assumes the downloaded game was already extracted and updates files from it.
    '''
    print('Applying the update...')
    sourcemod_path = os.path.join( SOURCEMOD_PATH , "pf2" ) 
    # temp path, connect to the internet to get the patch from later
    diff_path = ''
    # TEMPORARY TEMPORARY SUPPOSED TO BE PULLED OFF OF A SERVER
    if system() == 'Windows':
        diff_path = os.path.join( userpaths.get_downloads(), 'pf2_0' + str( LOCAL_VERSION ) + '-0' + str( SERVER_VERSION ) + '.patch' )
    else:
        diff_path = os.path.join( os.path.expanduser('~/Downloads/pf2_0' + str( LOCAL_VERSION ) + '-0' + str( SERVER_VERSION ) + '.patch' ) ) 

    replacement_path = os.path.join( TEMP_PATH, 'pf2_new', 'pf2' ) # Build we just downloaded in the temp path

    file = None
    # Have a file to tell you if an update was cancelled in the middle, then delete it when completely done.
    # Stores data about what version (72-73 as 0.7.2-0.7.3 for example) we were updating from 
    # If we have a DEBUG flag set, generate more information about the update.
    try:
        update_log = open( os.path.join( sourcemod_path, 'update_file' ), 'w' ) 
        update_log.write( str( LOCAL_VERSION ) + '-' + str( SERVER_VERSION ) + '\n' )
    except Exception as error:
        print( "An exception has occurred: ", error )

    success = False
    try:
        with open( diff_path, 'r' ) as file:
            diff_file = unidiff.PatchSet( file, metadata_only=True )
            for mod_file in diff_file.modified_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = mod_file.path.partition( '/' )[2].partition('/')[2]
                if DEBUG:
                    update_log.write( "Modified: " + relative_path + '\n' )
                # Update this file with the replacement one
                copy2( os.path.join( replacement_path, relative_path ), os.path.join( sourcemod_path, relative_path ) )
            for rem_file in diff_file.removed_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = rem_file.path.partition( '/' )[2].partition('/')[2]
                if DEBUG:
                    update_log.write( "Removed: " + relative_path + '\n' )
                # Remove this file.
                os.remove( os.path.join( sourcemod_path, relative_path ) )
            for added_file in diff_file.added_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = added_file.path.partition( '/' )[2].partition('/')[2]
                if DEBUG:
                    update_log.write( "Added: " + relative_path + '\n' )
                # Add the file
                copy2( os.path.join( replacement_path, relative_path ), os.path.join( sourcemod_path, relative_path ) )
            success = True
    except Exception as error:
        print( 'An exception has occurred: ', error )

    return success


def continue_update() -> bool:
    '''
    Function to set up variables so that the update can be continued. 
    '''
    # Get the global variables
    global LOCAL_VERSION
    global SERVER_VERSION

    # Get the pf2 path
    sourcemod_path = os.path.join( SOURCEMOD_PATH, 'pf2' )
    # Get the update file so we can continue updating
    update_file = open( os.path.join( sourcemod_path, 'update_file' ) )
    # Read the update file.
    buffer = update_file.readlines()
    # Extract the versions from the first line
    version = buffer[0].partition('-')
    # Set the variables
    LOCAL_VERSION = int( version[0] )
    SERVER_VERSION = int ( version[2] ) 
    # Continue updating.
    return update() 


def copy_to_destination( destination_path: str ) -> bool:
    '''
    Function to download PF2 into the sourcemods folder if it's not true.
    True if it was done successfully, False if something went wrong
    '''
    print( 'Extracting Pre-Fortress 2 to the sourcemods folder...' )
    success = False
    try:
        copytree( os.path.join( TEMP_PATH, 'pf2_new', 'pf2' ), destination_path, dirs_exist_ok=True )
        success = True
    except Exception as error:
        print('An exception has occurred: ', error)
    
    return success
        

def cleanup() -> None:
    '''
    TODO: Rewrite this function because it calls for some files that may or may not exist
    Function to clean up some files after we're done with them
    '''
    #sourcemod_path = os.path.join( SOURCEMOD_PATH, 'pf2' )
    #os.remove( os.path.join( sourcemod_path, 'update_file' ) )
    #os.remove( os.path.join( TEMP_PATH, 'pf2_new' ) ) 
    

def start() -> None:
    # set up the global variables.
    setupsourcemodpath()

    # Check for an update and check the update code with it
    match check_for_update():
        # Don't do anything if we don't need an update.
        case UpdateCode.NO_UPDATE:
            print( 'Your game is already up to date. Goodbye!' )
            return
        # Needs update, download and extract the latest build and apply changes 
        case UpdateCode.NEEDS_UPDATE: 
            if not message.message_yes_no( 'There is a new Pre-Fortress 2 update available. Do you wish to update?' ):
                print( 'no consent' )
                return
            if not download():
                print( 'no download' )
                return
            if not extract():
                print( 'no extract' )
                return
            if not update():
                print( 'no update' )
                return
        # The update was interrupted, continue
        case UpdateCode.NEEDS_UPDATE_INTERRUPTED:
            if not continue_update():
                print('no update')
                return
        # Should we download the game if it is installed?
        case UpdateCode.PROMPT_DOWNLOAD:
            # Ask the user if they want to download the game.
            if message.message_yes_no('Pre-Fortress 2 is not installed. Do you wish to download the game to your sourcemods folder?'):
                # Download the game
                if not download():
                    print('no download')
                    return
                # Extract the game
                if not extract():
                    print('no extract')
                    return
                # Download the game to the sourcemod path.
                if not copy_to_destination( os.path.join( SOURCEMOD_PATH, 'pf2' ) ):
                    print('no copy')
                    return
                
    # Clean up the files we left behind if any
    #cleanup()


if __name__ == "__main__":
    # Start the program if we executed this script
    start()