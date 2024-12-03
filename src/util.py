'''
Helpful functions used for the updater
'''
import os
from shutil import rmtree
from platform import system
import requests
import tarfile
from tqdm import tqdm
import unidiff
if system() == 'Windows':
    import winreg
    import userpaths # Get the downloads folder on Windows 
from shutil import rmtree, copy2, copytree
from dataclasses import dataclass
import vars
from vars import UpdateCode # Not writing vars.UpdateCode.UPDATE_YES screw that
import vpk
import requests
import message as message

# structure of an update file.
@dataclass
class UpdateInfo:
    hotfix_flag: bool # number to indicate the hotfix version (currently only used by 0.7-HOTFIX)
    old_version: int # Old version that we're updating from
    new_version: int # New version that we're being updated to
    last_file_num: int # Last file that was operated on
    operation: int # 0 for modified, 1 for removed, 2 for added

def setup_game_path() -> None:
    '''
    Sets the SOURCEMOD_PATH and GAME_PATH global variables. Stolen from TF2CDownloader.
    '''
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
            vars.SOURCEMOD_PATH = value[0]
            vars.GAME_PATH = os.path.join( value[0], 'pf2' )
        except Exception:
            # Exception, print something here
            message.print_exception_error_dbg()
    else: # Linux. We don't have a registry, so Steam has a fake one via registry.vdf
        try:
            sourcepath = None
            # Open the registry.vdf file, which holds the fake registry 
            with open( os.path.expanduser( r'~/.steam/registry.vdf' ), encoding="utf-8" ) as file:
                # Look for SourceModInstallPath.
                for _, line in enumerate( file ):
                    if 'SourceModInstallPath' in line:
                        # If we find it, replace the paths with proper slashes for UNIX systems
                        sourcepath = line[line.index('/home'):-1].replace(r'\\', '/').replace('\"', '')
                        break
            # Set the global variable.
            vars.SOURCEMOD_PATH = sourcepath
            vars.GAME_PATH = os.path.join( sourcepath, 'pf2' )
        except Exception:
            message.print_exception_error_dbg()

def get_local_version_num() -> int:
    '''
    Get the server's version in a number. Useful for patch identification and comparisons. 
    '''
    # Remove the periods from the string, and convert it to a number
    result = int( vars.LOCAL_VERSION_STRING.replace( '.', '' ).replace( '-HOTFIX', '' ) )
    # If this is a number divisible by 10, add a 0 at the end
    if len( str( result ) ) < 2:
        result *= 10

    return result

def get_server_version_num() -> int:
    '''
    Get the server's version in a number. Useful for patch identification and comparisons. 
    '''
    # Remove the periods from the string, and convert it to a number
    result = int( vars.SERVER_VERSION_STRING.replace( '.', '' ) )
    # If this is a number divisible by 10, add a 0 at the end
    if len( str( result ) ) < 2:
        result *= 10 

    return result

def delete_file_if_exists( file_path: str ) -> None:
    '''
    Delete files if they exist.
    '''
    if os.path.exists( file_path ):
        os.remove( file_path )

def delete_folder_if_exists( folder_path: str ) -> None:
    '''
    Delete folders (AND ALL OF ITS CONTENTS) if they exist.
    '''
    if os.path.exists( folder_path ):
        rmtree( folder_path )

def check_game_installation() -> bool:
    '''
    Checks if the game is installed. 
    '''
    # TODO: make a more comprehensive survey of game installation later
    server_binary_path = ''
    client_binary_path = ''

    # Since they're different binaries on different OSes, maybe someone deleted the ones they don't use.
    # Check for the system specific ones.
    if system() == 'Windows':
        server_binary_path = os.path.join( vars.GAME_PATH, 'bin', 'server.dll' )
        client_binary_path = os.path.join( vars.GAME_PATH, 'bin', 'client.dll' )
    else:
        server_binary_path = os.path.join( vars.GAME_PATH, 'bin', 'server.so' )
        client_binary_path = os.path.join( vars.GAME_PATH, 'bin', 'client.so' )

    # Check gameinfo.txt and ctf_2fort.bsp
    gameinfo_path = os.path.join( vars.GAME_PATH, 'gameinfo.txt' )
    ctf_2fort_path = os.path.join( vars.GAME_PATH, 'maps', 'ctf_2fort.bsp' )

    # Do we have PF2 installed?
    # check some important files if we have PF2 installed.
    return  os.path.exists( vars.GAME_PATH ) and \
            os.path.exists( server_binary_path ) and \
            os.path.exists( client_binary_path ) and \
            os.path.exists( gameinfo_path ) and \
            os.path.exists( ctf_2fort_path )

def check_game_version() -> str:
    '''
    Checks the game version, and updates the appropriate variables in vars.py.
    Returns the version string from the installed game.
    '''
    # We can't do anything if the game isn't installed!!!
    # Update function already checks this, comment this out for now
    #if not check_game_installation():
    #    return ''

    # Open the vpk file to get the version.txt file.
    # Note: pre-0.7.4 builds store it in the vpks
    # VPK path for the version.
    vpkpath = os.path.join( vars.GAME_PATH, "pf2_misc_dir.vpk" )
    version = ''
    # Open the vpk file containing the version.txt
    try:
        with vpk.open( vpkpath ) as vpkfile:
            # Get the file.
            version_file = vpkfile.get_file( 'version.txt' )
            # Get the version string from the file and convert it into an integer
            # Read the file, decode the file, format it as unicode, partition the important number part
            # and remove the periods from the version so that we can store the number
            version = vars.LOCAL_VERSION_STRING = version_file.read().decode().format('utf-8').partition('=')[2]
    except FileNotFoundError:
        # If this exception was raised, that means that we didn't find the file in the VPK.
        # try again in the root directory
        # Get the version.txt file
        normpath = os.path.join( vars.GAME_PATH, 'version.txt' )
        try:
            # Open the file.
            with open( normpath, 'r' ) as file:
                # Get the version string.
                version = vars.LOCAL_VERSION_STRING = file.read().partition('=')[2]
        except Exception:
            # Exception happened, traceback print
            message.print_exception_error_dbg()

    # Check if this is specifically the 0.7 hotfix build
    # We need to check for specifically this file in the custom folder
    if version == '0.7' and os.path.exists( os.path.join( vars.GAME_PATH, 'custom', '07hotfix_patch_dir.vpk' ) ):
        version += '-HOTFIX'
    
    return version

def check_server_version() -> str:
    '''
    Function to ask the server for the latest version via a text file
    '''
    server_version = ''
    # try to match that version.txt file from the server
    try:
        # Request version.txt from the website
        with requests.get( vars.WEBSITE_URL + 'version.txt' ) as response:
            # Strip new lines so we only get the server version.
            server_version = response.text.strip( '\n' )    
    except Exception as error:
        message.print_exception_error_dbg()

    return server_version

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

    # Check if the game is installed.
    if not check_game_installation():
        return UpdateCode.UPDATE_GAME_NOT_INSTALLED

    # Set the game version's string
    vars.LOCAL_VERSION_STRING = check_game_version()
    # Set the server version's string
    vars.SERVER_VERSION_STRING = check_server_version()

    # Check for an update file. If we have one, continue updating the game
    if parse_update_file():
        print( 'Continuing your update...\n' )
        return UpdateCode.UPDATE_INTERRUPTED

    # Check if we need an update. UPDATE_YES only if local version is less than the server version.
    # Added a check for specifically the hotfix. It is always considered out of date for now
    return UpdateCode.UPDATE_YES if get_local_version_num() < get_server_version_num() else UpdateCode.UPDATE_NO     

def download_file( url: str ) -> bool:
    '''
    Function to download a file off the internet and write it to disk. 
    True if we were able to fully download the file (HTTP 200 success code), False if we didn't 
    '''
    try:
        # Try requesting the server to get a file.
        response = requests.get( url, stream=True, timeout=10 )

        # how big is this file?
        total_size = int( response.headers.get( 'content-length', 0 ) )
        # show a progress bar to the console using tqdm.
        with open( os.path.basename( url ), "wb" ) as handle,    tqdm( 
                                                                            desc=f'Downloading {os.path.basename( url )}', 
                                                                            total=total_size,
                                                                            unit='iB',
                                                                            unit_scale=True ) as bar:
            # Write to the disk.
            for chunk in response.iter_content( chunk_size=1*1024 ):
                size = handle.write( chunk )
                bar.update( size )
                
    # did we time out? Did the server just not have it? etc...
    except Exception as error:
        message.print_exception_error_dbg()

    # Did we succeed?
    return response.status_code == 200


def download() -> bool: 
    '''
    Downloads the update's tar file, True if we downloaded it fully, False if something went wrong
    '''
    print( 'Downloading...' )
    
    if vars.DEBUG and os.path.exists( vars.FILE_NAME ):
        return True

    return download_file( vars.FILE_URL )

def extract() -> bool:
    '''
    Extracts the tar file into a new folder.
    '''
    print('Extracting the game...')

    if vars.DEBUG and os.path.exists( 'pf2_new' ):
        return True
    
    # Flag to indicate success.
    success = False
    try:
        # Open the tar file that we just downloaded.
        with tarfile.open( vars.FILE_NAME ) as file:
            # Try extracting it
            file.extractall( 'pf2_new' )
            os.chmod( 'pf2_new', 0o755 )
            # If we extracted it, set the flag for success.
            success = True
    except Exception:
        message.print_exception_error_dbg()

    return success

def update( update_info : UpdateInfo = None ) -> bool:
    '''
    Try to update the game with the downloaded build 
    via a diff file downloaded from the server.
    This assumes the downloaded game was already extracted and updates files from it.
    '''
    print( 'Applying the update...' )

    # Is this the hotfix version?
    old_version_hotfix_flag = vars.LOCAL_VERSION_STRING.endswith( '-HOTFIX' )

    # append 1 to the local version num if we're updating from the 0.7 hotfix from an interrupted update
    hotfix_add = ''
    if old_version_hotfix_flag:
        hotfix_add = '1'

    # Download a temp patch file.
    diff_path = 'pf2_0' + str( get_local_version_num() ).replace( '.', '' ) + hotfix_add + '-0' + str( get_server_version_num() ) + '.patch'

    print( 'Downloading the patch file for temporary usage...' )
    # Download a patch file, we're gonna use this to patch the game.
    download_file( f'https://raw.githubusercontent.com/Pre-Fortress-2/Updater/main/{diff_path}' )
    # Build we just downloaded in the temp path
    replacement_path = os.path.join( 'pf2_new', 'pf2' ) 

    # Debug log file storage
    update_dbg_log = None
    # Debugging log to check what files were modified, removed, or added
    if vars.DEBUG:
        try:
            update_dbg_log = open( os.path.join( vars.GAME_PATH, 'update_debug_log.log' ), 'w' ) 
            update_dbg_log.write( str( get_local_version_num() ) + '-' + str( get_server_version_num() ) + '\n' )
        except Exception:
           message.print_exception_error_dbg()
           update_dbg_log.close()

    # Success flag
    success = False
    try:
        # Open the patch file.
        with open( diff_path, 'r' ) as file:
            diff_file = unidiff.PatchSet( file, metadata_only=True )
            for idx, mod_file in enumerate( diff_file.modified_files ):
                # Get the relative path so we can easily join the new folder with the old folder.
                # If we're continuing from where we started, check the last thing we were on
                if update_info:
                    # If we're not modifying, go to the next one
                    if update_info.operation != 0:
                        break
                    # Don't do anything if we're not where we continued from
                    if idx < update_info.last_file_num:
                        continue

                # Get the relative path
                relative_path = mod_file.path.partition( '/' )[2].partition('/')[2]

                # write what we did to the update file
                write_to_update_file( old_version_hotfix_flag, int( get_local_version_num() ), get_server_version_num(), idx, 0 )

                # Get the currently installed game's path in TEMP
                replace_path = os.path.join( replacement_path, relative_path )
                # And the installed game we're trying to update.
                install_path = os.path.join( vars.GAME_PATH, relative_path )

                # Sometimes, diff files say a file is modified when 
                # in fact the file doesn't exist in the new one
                # Delete it if this happens
                if not os.path.exists( replace_path ):
                    # Write to our debug log to see what was touched
                    if vars.DEBUG:
                        update_dbg_log.write( "Removed: " + relative_path + '\n' )
                    # Delete it from our build as we no longer need it anymore
                    os.remove( install_path )
                    continue
                # Write to our debug log to see what was touched
                if vars.DEBUG:
                    update_dbg_log.write( "Modified: " + relative_path + '\n' )
                # Update this file with the replacement one
                copy2( replace_path, install_path )
            for idx, rem_file in enumerate( diff_file.removed_files ):
                # Get the relative path so we can easily join the new folder with the old folder.
                # If we're continuing from where we started, check the last thing we were on
                if update_info:
                    # If we're not modifying, go to the next one
                    if update_info.operation != 1:
                        break
                    # Don't do anything if we're not where we continued from
                    if idx < update_info.last_file_num:
                        continue
                # Get the relative path
                relative_path = rem_file.path.partition( '/' )[2].partition('/')[2]
                
                # Get the currently installed game's path in TEMP
                replace_path = os.path.join( replacement_path, relative_path )
                # And the installed game we're trying to update
                install_path = os.path.join( vars.GAME_PATH, relative_path )

                # Remove this file.
                if vars.DEBUG:
                    update_dbg_log.write( "Removed: " + relative_path + '\n' ) 
                # Write our progress in the update file
                write_to_update_file( old_version_hotfix_flag, int( get_local_version_num() ), get_server_version_num(), idx, 1 )

                # Remove the file.
                os.remove( os.path.join( vars.GAME_PATH, relative_path ) )
            for idx, added_file in enumerate( diff_file.added_files ):
                # If we're continuing from where we started, check the last thing we were on
                if update_info:
                    # This shouldn't happen, but break if we're here and somehow operation isn't 2
                    if update_info.operation != 2:
                        break
                    # Go to the file from the update info
                    if idx < update_info.last_file_num:
                        continue
                # Get the relative path so we can easily join the new folder with the old folder.
                relative_path = added_file.path.partition( '/' )[2].partition('/')[2]
                
                # Write to our debug log
                if vars.DEBUG:
                    update_dbg_log.write( "Added: " + relative_path + '\n' )
                
                # Write to the update file.
                write_to_update_file( old_version_hotfix_flag, int( get_local_version_num() ), get_server_version_num(), idx, 2 )

                # New downloaded game path
                replace_path = os.path.join( replacement_path, relative_path )
                # Install path
                install_path = os.path.join( vars.GAME_PATH, relative_path )

                # If we don't have a folder for this new file, make one
                if not os.path.exists( os.path.join( install_path, '../' ) ):
                    os.mkdir( os.path.join( install_path, '../' )  )

                # Get the file
                copy2( replace_path, install_path )
            # Set the flag after we're done
            success = True
    except Exception:
        # Something happened, error out
        message.print_exception_error_dbg()

    # Delete the update file. We're done with it.
    delete_file_if_exists( os.path.join( vars.GAME_PATH, 'update_file' ) )
    # Delete that patch file too.
    delete_file_if_exists( diff_path )

    # Close the update debug log
    if vars.DEBUG:
        update_dbg_log.close()

    # Yay, we successfully updated!
    return success


def continue_update() -> bool:
    '''
    Function to set up variables so that the update can be continued. 
    '''
    print( 'It appears an update was interrupted. Continuing.' )
    # Get the update file so we can continue updating
    update_info = parse_update_file()

    # Check if some files are still there
    # Redownload if this doesn't exist
    if not os.path.exists( vars.FILE_NAME ):
        download()
    
    # extract if this doesn't exist.
    if not os.path.exists( 'pf2_new' ):
        extract()
    
    # Add -HOTFIX to the local version we have.
    if update_info.hotfix_flag:
        vars.LOCAL_VERSION_STRING += '-HOTFIX' 
    
    # Continue updating.
    return update( update_info=update_info ) 

def install() -> bool:
    '''
    Function to install PF2 into the sourcemods folder. If there is already a build there, then
    the user will be asked if they wish to delete it and install over it. Otherwise, nothing will happen.
    True if it was done successfully, False if something went wrong
    '''
    print( 'Installing Pre-Fortress 2 to the sourcemods folder...' )

    # This is where the extracted contents are. 
    temp_install = os.path.join( 'pf2_new', 'pf2' )

    # success flag to indicate that we did this completely.
    success = False
    try:
        if os.path.exists( vars.GAME_PATH ):
            if message.message_yes_no( 'WARNING: Pre-Fortess 2 will be removed. Do you wish to continue?' ):
                # Delete everything in the folder after consent has been given
                for file in os.listdir( vars.GAME_PATH ):
                    # Relative path to the game directory
                    rel_path = os.path.join( vars.GAME_PATH, file )
                    # Call the proper removal function if it's a file or directory.
                    if os.path.isfile( rel_path ):
                        os.unlink( rel_path )
                    if os.path.isdir( rel_path ):
                        rmtree( rel_path )
            else: # If no, return early, the user didn't want to remove the game.
                return True
            
        else: # PF2 wasn't detected, make the pf2 folder
            os.mkdir( vars.GAME_PATH )

        # Copy the contents to the game directory.
        for file in os.listdir( temp_install ):
            # Relative path to the new downloaded version
            rel_path = os.path.join( temp_install, file )
            # Destination path to the game path
            dest_path = os.path.join( vars.GAME_PATH, file )
            # Do the appropriate copy function for a file or directory.
            if os.path.isfile( rel_path ):
                copy2( rel_path, dest_path )
            if os.path.isdir( rel_path ):
                copytree( rel_path, dest_path )
        # Mark that we succeeded
        success = True
    except Exception:
        message.print_exception_error_dbg()
    return success

def write_to_update_file( hotfix_flag: bool, old_version: int, new_version: int, idx: int, operation: int ) -> None:
    '''
    Function to write to an update file while we're updating the game.
    Overwrite every time we update anything to keep our space to continue
    Arguments:
    hotfix_flag indicates that this version is a hotfix.
    old_version is the version we're updating from
    new_version is the version we're updating to
    idx is part of the index of files we left off from in updater.py's update function
    operation is either 0, 1, or 2 which is modified, removed, added, respectively
    '''
    # Go to the update file path
    update_file_path = os.path.join( vars.GAME_PATH, 'update_file' )
    # Write the format as binary to the file_path
    with open( update_file_path, 'wb') as file:
        file.write( hotfix_flag.to_bytes( 2 ) + old_version.to_bytes( 2 ) + new_version.to_bytes( 2 ) + idx.to_bytes( 2 ) + operation.to_bytes( 2 ) )

def parse_update_file() -> UpdateInfo:
    '''
    Function to parse the update file so that we can continue from where we stopped.
    '''
    update_path = os.path.join( vars.GAME_PATH, 'update_file' )
    # How?
    if not os.path.exists( update_path ):
        return None
    # Append the bytes to a list
    result = []
    # Open the update file
    with open( update_path, 'rb' ) as update_file:
        # Loop through the file by two bytes
        while byte := update_file.read( 2 ):
            result.append( byte )
            
    # Return an UpdateInfo object based on the file we just read
    return UpdateInfo( result[0], result[1], result[2], result[3], result[4] )
        
def delete_all_temp_files() -> None:
    '''
    Function to delete all temp files (.cache and .tmp)
    '''
    if not check_game_installation():
        return

    # Look through all directories for any temp files
    for root, __, files in os.walk( vars.GAME_PATH ):
        for tmp_file in files:
            # Is this file a temp file?
            if tmp_file.endswith( '.cache' ) or tmp_file.endswith( '.tmp' ):
                # If so, delete it
                os.remove( os.path.join( root, tmp_file ) )

    print( 'Cleared all cache files.' )