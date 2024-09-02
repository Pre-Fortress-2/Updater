'''
Updater for Pre-Fortress 2. Windows and Linux compatible.
'''
import os
import message
import vars
from vars import UpdateCode
import util

def download_game():
    '''
    Download and extract the game.
    '''
    util.download()
    util.extract()

def install_game():
    '''
    Download and install the game.
    '''
    download_game()
    util.install()

def update_game( continue_update : bool = False ) -> None:
    '''
    Download and update the game.
    '''
    download_game()

    # If we were interrupted, pass the update file to the continue_update function
    if continue_update:
        util.continue_update()
    else:
    # Else update normally.
        util.update()

def cleanup() -> None:
    '''
    Function to clean up some files after we're done with them
    '''
    if not vars.DEBUG:
        util.delete_folder_if_exists( os.path.join( vars.TEMP_PATH, 'pf2_new' ) ) 
        util.delete_file_if_exists( os.path.join( vars.TEMP_PATH, vars.FILE_NAME ) )
    
    util.delete_all_temp_files()

def main() -> None:
    # set up the sourcemod path global var
    util.setup_game_path()

    while True:
        result = message.message_options( 'Welcome to the Pre-Fortress 2 updater! Select your option.',
                                        'Check for updates',
                                        'Install the game',
                                        'Clear cache files',
                                        'Exit' )
        match result:
            case 1: # Check for updates.
                match util.check_for_update():
                    case UpdateCode.UPDATE_GAME_NOT_INSTALLED:
                        # Game isn't installed, tell the user to use the "Install the game" option
                        print( 'Pre-Fortress 2 is not installed on this device. Please select the option \'Install the game.\'' )
                    case UpdateCode.UPDATE_NO:
                        # Game is already up to date.
                        print( 'Your game is up to date.' )
                    case UpdateCode.UPDATE_YES:
                        # Game is out of date. Ask if the user wants to update.
                        print( f'Current version: {vars.LOCAL_VERSION_STRING}' )
                        print( f'Latest version: {vars.SERVER_VERSION_STRING}' )
                        if message.message_yes_no( 'Your game is out of date! Do you wish to update?' ):
                            # Update the game!
                            update_game()
                        else:
                            # Go back to the main menu if the user says no
                            print( 'Okay. Going back to the main menu.' )
                    case UpdateCode.UPDATE_INTERRUPTED:
                        update_game( True )

            case 2: # Install the game
                install_game()
            case 3:
                # Delete all temp files in the installed game.
                util.delete_all_temp_files()
            case 4:
                break
            case default:
                print( 'Invalid option! Try again.' )

if __name__ == "__main__":
    main()
   