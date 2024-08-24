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
    
def message_options( question: str, *answers : str ) -> int:
    print( question )
    for idx, ans in enumerate( answers ):
        print( str(idx + 1) + '. ', ans )
    
    result = int( input() )
    if result > len( answers ) or result < 0:
        return -1 # Failed.

    return result