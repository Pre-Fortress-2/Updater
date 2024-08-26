'''
Extremely simple message library used in this project so I don't have to type out all of these
'''
import os
from vars import DEBUG

def message_yes_no( msg: str ) -> bool:
    '''
    Shows a message expecting a Y (YES) or N (NO) response.
    If invalid, assume no.
    '''
    msg += ' Y/N\n' # append Y/N to the question
    ans = input( msg )
    return ans.upper()[0] == 'Y'
    
def message_options( question: str, *answers : str ) -> int:
    '''
    Show a message with answer options.
    Normally returns the number of which the user inputted if it's valid within the answer choices,
    otherwise returns -1.
    '''
    # show the question
    print( question )

    # Print the answers along with their corresponding number.
    for idx, ans in enumerate( answers ):
        # Add by one because computers start from 0... 
        print( str( idx + 1 ) + '. ', ans )
    
    # What did the user type? Always expect a number.
    result = input()

    # Did the user type a number?
    if not result.isdigit():
        return -1
    
    # Convert to a number
    result = int( result )

    # If the result is more than the answers or the result is 0, register it as -1
    if result > len( answers ) or result < 0:
        return -1 # Failed, wrong option.

    # return the result
    return result

def print_exception_error_dbg( err: Exception ) -> None:
    # Print an exception error if the debug flag is on.
    if DEBUG:
        print( "An exception occurred: ", err )