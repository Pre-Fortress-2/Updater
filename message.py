import os


def message_yes_no( msg: str ) -> bool:
    msg += ' Y/N\n' #append this to it
    ans = input( msg )
    if ans.upper()[0] == 'Y':
        return True
    elif ans.upper()[0] == 'N':
        return False
    else:
        print( 'Invalid response.' )
        return False