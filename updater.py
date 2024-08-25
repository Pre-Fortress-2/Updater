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
    import userpaths # Get the downloads folder on windows 
import unidiff
from shutil import copy2, rmtree, move
from enum import Enum

#import rich # remember to import rich so that we can have pretty text or something IDK

import message
import vars
import util

# Update codes the check_for_update function will use to do the appropriate action
class UpdateCode( Enum ):
    UPDATE_NO = 0, # Game is up to date.
    UPDATE_YES = 1, # Game needs an update.
    UPDATE_INTERRUPTED = 2, # Game's update was interrupted somehow, restore
    UPDATE_GAME_NOT_INSTALLED = 3, # Game isn't installed

def check_for_update() -> int:
    '''
    Check if we need an update.
    but was cancelled due to an error or was closed out prematurely
    Can return:
    UPDATE_NO means PF2 is up to date.
    UPDATE_YES means PF2 needs an update.
    UPDATE_INTERRUPTED means that PF2's update was interrupted.
    UPDATE_GAME_NOT_INSTALLED means that the game isn't installed.
    '''
    # Traverse to the PF2 path
    sourcemod_path = os.path.join( vars.SOURCEMOD_PATH, 'pf2' )

    # Check if the game is installed.
    if not util.check_game_installation():
        return UpdateCode.UPDATE_GAME_NOT_INSTALLED

    # Check for an update file. If we have one, continue updating the game
    if os.path.exists( os.path.join( sourcemod_path, 'update_file' ) ):
        print( 'Continuing your update...\n' )
        return UpdateCode.UPDATE_INTERRUPTED

    # Open the vpk file to get the version.txt file.
    # Note: pre-0.7.4 builds store it in the vpks
    try:
        # VPK path for the version.
        vpkpath = os.path.join( sourcemod_path, "pf2_misc_dir.vpk" )
        # Open the vpk file containing the version.txt
        vpkfile = vpk.open( vpkpath )
        # Get the file.
        file = vpkfile.get_file( 'version.txt' )
        # Get the version string from the file and convert it into an integer
        # Read the file, decode the file, format it as unicode, partition the important number part
        # and remove the periods from the version so that we can store the number
        vars.LOCAL_VERSION_STRING = file.read().decode().format('utf-8').partition('=')[2]
        vars.LOCAL_VERSION = int( vars.LOCAL_VERSION_STRING.replace( '.', '' ) )
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
            vars.LOCAL_VERSION_STRING = file.read().partition('=')[2]
            # convert this version text to a number.
            vars.LOCAL_VERSION = int( vars.LOCAL_VERSION_STRING.replace( '.', '' ) )
            # close the file.
            file.close()
        except Exception as error:
            # Game might be missing files if we can't find version.txt
            message.print_exception_error_dbg( error )
            return UpdateCode.UPDATE_GAME_NOT_INSTALLED

    # try to match that version.txt file from the server
    try:
        # Request version.txt from the website
        response = requests.get( vars.WEBSITE_URL + 'version.txt' )
        # Get the text from it and strip new lines from it.
        vars.SERVER_VERSION_STRING = response.text.strip('\n')
        response.close()
        vars.SERVER_VERSION = int( vars.SERVER_VERSION_STRING.replace( '.', '' ) )
        # Is our local version less than the one off the website?
        if vars.LOCAL_VERSION < vars.SERVER_VERSION:
            return UpdateCode.UPDATE_YES # We need to update!!!
        
    except Exception as error:
        message.print_exception_error_dbg( error )

    # We don't need an update.
    return UpdateCode.UPDATE_NO     


def download() -> bool: 
    '''
    Downloads the update, True if we downloaded it correctly, False if we didn't
    '''
    if os.path.exists( os.path.join( vars.TEMP_PATH, 'latest.tar.gz' ) ):
        return True

    try:
        # Try requesting the server to get a file.
        response = requests.get( vars.FILE_URL, stream=True, timeout=10 )

        total_size = int( response.headers.get( 'content-length', 0 ) )
        # show a progress bar to the console using tqdm.
        with open( os.path.join( vars.TEMP_PATH, 'latest.tar.gz' ), "wb" ) as handle, tqdm( 
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
        message.print_exception_error_dbg( error )

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
        with tarfile.open( os.path.join( vars.TEMP_PATH, 'latest.tar.gz' ) ) as file:
            # Try extracting it
            file.extractall( os.path.join( vars.TEMP_PATH, 'pf2_new' ) )
            # If we extracted it, set the flag for success.
            success = True
    except FileNotFoundError:
        # If we didn't find the file, stop
        print('Unable to open the file! Please try running this program again.')
    except tarfile.ExtractError:
        # If we're unable to extract the file, stop
        print( 'Unable to extract the file. Please try running this program again.' )
    except Exception as error:
        message.print_exception_error_dbg( error )

    return success


def update() -> bool:
    '''
    Try to update the game with the downloaded build 
    via a diff file downloaded from the server.
    This assumes the downloaded game was already extracted and updates files from it.
    '''
    print('Applying the update...')
    sourcemod_path = os.path.join( vars.SOURCEMOD_PATH , "pf2" ) 
    # temp path, connect to the internet to get the patch from later
    diff_path = ''
    # TEMPORARY TEMPORARY SUPPOSED TO BE PULLED OFF OF A SERVER
    if system() == 'Windows':
        diff_path = os.path.join( 'E:\\Downloads', 'pf2_0' + str( vars.LOCAL_VERSION ) + '-0' + str( vars.SERVER_VERSION ) + '.patch' )
    else:
        diff_path = os.path.expanduser('~/Downloads/pf2_0' + str( vars.LOCAL_VERSION ) + '-0' + str( vars.SERVER_VERSION ) + '.patch' ) 

    replacement_path = os.path.join( vars.TEMP_PATH, 'pf2_new', 'pf2' ) # Build we just downloaded in the temp path

    file = None
    # Have a file to tell you if an update was cancelled in the middle, then delete it when completely done.
    # Stores data about what version (72-73 as 0.7.2-0.7.3 for example) we were updating from 
    # If we have a DEBUG flag set, generate more information about the update.
    try:
        update_log = open( os.path.join( sourcemod_path, 'update_file' ), 'w' ) 
        update_log.write( str( vars.LOCAL_VERSION ) + '-' + str( vars.SERVER_VERSION ) + '\n' )
    except Exception as error:
        print( "An exception has occurred: ", error )

    success = False
    try:
        with open( diff_path, 'r' ) as file:
            diff_file = unidiff.PatchSet( file, metadata_only=True )
            for mod_file in diff_file.modified_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = mod_file.path.partition( '/' )[2].partition('/')[2]
                if vars.DEBUG:
                    update_log.write( "Modified: " + relative_path + '\n' )
                # Update this file with the replacement one
                move( os.path.join( replacement_path, relative_path ), os.path.join( sourcemod_path, relative_path ) )
            for rem_file in diff_file.removed_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = rem_file.path.partition( '/' )[2].partition('/')[2]
                if vars.DEBUG:
                    update_log.write( "Removed: " + relative_path + '\n' )
                # Remove this file.
                os.remove( os.path.join( sourcemod_path, relative_path ) )
            for added_file in diff_file.added_files:
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = added_file.path.partition( '/' )[2].partition('/')[2]
                if vars.DEBUG:
                    update_log.write( "Added: " + relative_path + '\n' )
                # Add the file
                move( os.path.join( replacement_path, relative_path ), os.path.join( sourcemod_path, relative_path ) )
            success = True
    except Exception as error:
        print( 'An exception has occurred: ', error )

    # Close the update file so it can be cleared later
    update_log.close()

    return success


def continue_update() -> bool:
    '''
    Function to set up variables so that the update can be continued. 
    '''
    # Get the pf2 path
    sourcemod_path = os.path.join( vars.SOURCEMOD_PATH, 'pf2' )
    # Get the update file so we can continue updating
    update_file = open( os.path.join( sourcemod_path, 'update_file' ) )
    # Read the update file.
    buffer = update_file.readlines()
    # Extract the versions from the first line
    version = buffer[0].partition('-')
    # Set the variables
    vars.LOCAL_VERSION = int( version[0] )
    vars.SERVER_VERSION = int ( version[2] ) 
    # Continue updating.
    update_file.close()
    return update() 


def move_to_destination( destination_path: str ) -> bool:
    '''
    Function to move PF2 into the sourcemods folder if it wasn't installed.
    True if it was done successfully, False if something went wrong
    '''
    print( 'Moving Pre-Fortress 2 to the sourcemods folder...' )
    success = False
    try:
        if os.path.exists( destination_path ):
            if message.message_yes_no( 'WARNING! THE GAME AT PATH \"' + destination_path + '\" WILL BE DELETED! DO YOU WISH TO CONTINUE?' ):
                rmtree( destination_path )
                move( os.path.join( vars.TEMP_PATH, 'pf2_new', 'pf2' ), destination_path )
                success = True
    except Exception as error:
        print('An exception has occurred: ', error)
    
    return success
        

def cleanup() -> None:
    '''
    Function to clean up some files after we're done with them
    '''
    sourcemod_path = os.path.join( vars.SOURCEMOD_PATH, 'pf2' )
    util.delete_file_if_exists( os.path.join( sourcemod_path, 'update_file' ) )
    util.delete_folder_if_exists( os.path.join( vars.TEMP_PATH, 'pf2_new' ) ) 
    #util.delete_file_if_exists( os.path.join( vars.TEMP_PATH, 'latest.tar.gz' ) )

if __name__ == "__main__":
    # set up the sourcemod path global var
    util.setup_sourcemod_path()
    
    # Start this in a loop
    while True:
        
        # Start the program if we executed this script 
        # Get the answer of this message.
        result = message.message_options( 'Welcome to the Pre-Fortress 2 Updater! What would you like to do today?', 
                                'Check for updates', 
                                'Install the game',
                                'Exit' )
        # Get the result
        match result:
            case 1: # Check for updates
                match check_for_update():
                    case UpdateCode.UPDATE_NO: # We don't need an update.
                        print( 'Your game is up to date.' )
                        continue
                    case UpdateCode.UPDATE_YES: # We do need an update.
                        # Print the versions: the local version and the server's version
                        print( 'Current version: ', vars.LOCAL_VERSION_STRING )
                        print( 'Latest version: ', vars.SERVER_VERSION_STRING )
                        if message.message_yes_no( 'Your game is out of date. Do you wish to update?' ):
                            # If yes, start doing stuff
                            # Download the tar file
                            download()
                            # Extract the tar file
                            extract()
                            # Apply the update via the diff
                            update()
                        else:
                            continue # Give the user a menu.
                        break
                    case UpdateCode.UPDATE_INTERRUPTED: # An update was interrupted.
                        print( 'It appears an update was interrupted. Continuing...' )
                        continue_update()
                        break
                    case UpdateCode.UPDATE_GAME_NOT_INSTALLED: # Game was not installed.
                        print( 'Pre-Fortress 2 was not detected on your computer. Please select the option \'Install the game\' to install it.' ) 
                        continue
            case 2: # Install the game
                # Check if we have a game installation...
                if util.check_game_installation():
                    # Warn the user before prompting them to reinstall the game
                    print( 'WARNING: REINSTALLING WILL DELETE EVERYTHING FROM YOUR PRE-FORTRESS 2 INSTALL!!!' )
                    if message.message_yes_no( 'You appear to already have Pre-Fortress 2 installed. Do you wish to reinstall it?' ):
                        print('Got it. Downloading Pre-Fortress 2.')
                        download()
                        extract()
                        move_to_destination( os.path.join( vars.SOURCEMOD_PATH, 'pf2' ) )
                        break # Clean up.
                    else:
                        continue # ask again.
            case 3: # Exit
                break # we exited, get out of here lol
            case default:
                print( 'Invalid option.')
                continue

    # Clean up the files we left behind if any
    cleanup()
