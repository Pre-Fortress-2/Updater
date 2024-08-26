import os
from shutil import rmtree
from platform import system
if system() == 'Windows':
    import winreg
from dataclasses import dataclass
import vars

# structure of an update file.
@dataclass
class UpdateInfo:
    old_version: int # Old version that we're updating from
    new_version: int # New version that we're being updated to
    last_file_num: int # Last file that was operated on
    operation: int # 0 for modified, 1 for removed, 2 for added

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

def setup_sourcemod_path() -> None:

    '''
    Sets up the SOURCEMOD_PATH global variable. Stolen from TF2CDownloader.
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
        except Exception as error:
            # Exception, print something here
            print( "Exception occurred: ", error )
    else: # Linux. We don't have a registry, so Steam has a fake one via registry.vdf
        try:
            sourcepath = None
            # Open the registry.vdf file, which holds the fake registry 
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
            vars.SOURCEMOD_PATH = sourcepath

        except Exception as error:
            # Exception, print something here
            print( "Exception occurred: ", error )

def check_game_installation() -> bool:
    # Traverse to the PF2 path
    sourcemod_path = os.path.join( vars.SOURCEMOD_PATH, 'pf2' )
    server_binary_path = ''
    client_binary_path = ''

    # Since they're different binaries on different OSes, maybe someone deleted the ones they don't use.
    # Check for the system specific ones.
    if system() == 'Windows':
        server_binary_path = os.path.join( sourcemod_path, 'bin', 'server.dll' )
        client_binary_path = os.path.join( sourcemod_path, 'bin', 'client.dll' )
    else:
        server_binary_path = os.path.join( sourcemod_path, 'bin', 'server.so' )
        client_binary_path = os.path.join( sourcemod_path, 'bin', 'client.so' )

    # Check gameinfo.txt and ctf_2fort.bsp
    gameinfo_path = os.path.join( sourcemod_path, 'gameinfo.txt' )
    ctf_2fort_path = os.path.join( sourcemod_path, 'maps', 'ctf_2fort.bsp' )

    # Do we have PF2 installed?
    # check some important files if we have PF2 installed.
    return  os.path.exists( sourcemod_path ) and \
            os.path.exists( server_binary_path ) and \
            os.path.exists( client_binary_path ) and \
            os.path.exists( gameinfo_path ) and \
            os.path.exists( ctf_2fort_path )

def write_to_update_file( file_path: str, old_version: int, new_version: int, idx: int, operation: int ) -> None:
    if not os.path.exists( file_path ):
        return
    # Write the format as binary to the file_path
    with open( file_path, 'wb') as file:
        file.writelines( str(old_version), '', )


def parse_update_file( file_path: str ) -> UpdateInfo:
    if not os.path.exists( file_path ):
        return None
    
    with open( file_path, 'r' ) as update_file:
        update_info_buffer = update_file.readlines()
        if not update_info_buffer:
            return None
        update_file.close()
        return UpdateInfo( int( update_info_buffer()[0] ), 
                        int( update_info_buffer()[1] ), 
                        update_info_buffer()[2], 
                        int( update_info_buffer()[3] ) )
        