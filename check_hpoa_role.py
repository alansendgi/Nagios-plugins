#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-
# 
# Script for checking the role of the HP Onboard Administrator and
# sending the results to Nagios.
#
# Written by Alan Sendgikoski <asendgi@gmail.com>
# 
# Licence : GNU General Public Licence (GPL) http://www.gnu.org/
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# $ python check_hpoa_role.py -H hostname1oa02 -A <IPaddress> -U Administrator -P <password> -C '<SNMP community name>'
#     -H <hostname>                Device hostname
#     -A <ipaddress>               Device IP address
#     -U <username>                Device username
#     -P <password>                Device password
#     -C <community_name>          SNMP community name
# 
#

from __future__ import absolute_import
import getopt
import os
import pexpect
import re
import subprocess
import sys
import time


def exit_with_usage():

    print(globals()['__doc__'])
    os._exit(1)

def main():
    
    # Set variables
    critical = 5000.0
    warning = 3000.0
    sleeptime = 1
    
    # define Nagios exit codes and variables
    ExitOK = 0
    ExitWarning = 1
    ExitCritical = 2
    ExitUnknown = 3

    ######################################################################
    ## Parse the options, arguments, get ready, etc.
    ######################################################################
    
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'h?H:A:U:P:C:', ['help','h','?'])
    except Exception as e:
        print(str(e))
        exit_with_usage()
    options = dict(optlist)
    if len(args) > 1:
        exit_with_usage()

    if [elem for elem in options if elem in ['-h','--h','-?','--?','--help']]:
        print("Help:")
        exit_with_usage()

    if '-H' in options:
        hostname = options['-H']
    else:
        exit_with_usage()
    if '-A' in options:
        ipaddress = options['-A']
    else:
        exit_with_usage()
    if '-U' in options:
        username = options['-U']
    else:
        exit_with_usage()
    if '-P' in options:
        password = options['-P']
    else:
        exit_with_usage()
    if '-C' in options:
        community_name = options['-C']
    else:
        exit_with_usage()
    
    ############################################################################
    ## Login to platform
    ############################################################################
    
    # define some constants
    CONN_REFUSED = 'Connection refused'
    SSH_NEWKEY = '[Aa]re you sure you want to continue connecting \(yes/no\)\? '
    # sample command prompt: hostname1oa01> 
    COMMAND_PROMPT = hostname + '\>\s'
    
    child = pexpect.spawn('/usr/bin/ssh %s@%s' % (username, ipaddress))
    
    # uncomment the following line for debugging
    child.logfile = sys.stdout
    
    i = child.expect([CONN_REFUSED, pexpect.TIMEOUT, SSH_NEWKEY, COMMAND_PROMPT, '(?i)password'], timeout=2)
    if i == 0: # Connection refused
        #print('Connection refused')
        command_resp = 'CRITICAL: connection refused'
        command_exit = 2
        print('%s' % (command_resp))
        sys.exit('command_exit')
        # Now exit the remote host.
        child.sendline('exit')
    if i == 1: # Timeout
        #print('ERROR! could not login with SSH.')
        #print(child.before, child.after)
        #print(str(child))
        command_resp =('CRITICAL: could not login with SSH.')
        command_exit = 2
        print('%s' % (command_resp))
        sys.exit('command_exit')
        # Now exit the remote host.
        child.sendline('exit')
    if i == 2: # In this case SSH does not have the public key cached.
        child.sendline('yes')
        child.expect('[Pp]assword: ')
        child.sendline(password)
        # Now we are at the command prompt.
        child.expect(COMMAND_PROMPT)
        time.sleep(1)
    if i == 3:
        # This may happen if a public key was setup to automatically login.
        # But beware, the COMMAND_PROMPT at this point is very trivial and
        # could be fooled by some output in the MOTD or login message.
        pass
    if i == 4:
        child.sendline(password)
        # Now we are at the command prompt.
        #child.expect(COMMAND_PROMPT)
        i = child.expect(['[Pp]assword: ', COMMAND_PROMPT])
        if i == 0:
            # password prompt again, probably because the password was not accepted
            #print('Permission denied. Possible invalid password.')
            command_resp = 'CRITICAL: permission denied; possible invalid password.'
            command_exit = 2
            print('%s' % (command_resp))
            sys.exit('command_exit')
            # Now exit the remote host.
            child.sendline('exit')
        if i == 1:
            pass

    time.sleep(2)
    
    # Now we should be at the command prompt and ready to run some commands.
    
    ROLE_STANDBY = 'Not a valid request while running in standby mode'
    
    ############################################################################
    # HC03a - determine Onboard Administrator role (active or standby)
    #
    # hostname2oa01> show oa status
    # 
    # Onboard Administrator #1 Status:
    # 	Name:   hostname2oa01
    # 	Role:   Active
    # 	UID:    Off
    # 	Status: OK
    # 
    # 
    # hostname2oa01>
    ############################################################################
    
    # Issue command via ssh
    child.sendline('show oa status')
    
    # Read ssh response
    i = child.expect([ROLE_STANDBY, '\tRole:\s+Standby', '\tRole:\s+Active', pexpect.TIMEOUT])
    if i == 0 or i == 1:
        oa_role = 'OA is in standby mode'
        command03a_resp = "OA is in Standby, so SNMP checks are suppressed."
        command03a_exit = 3
    if i == 2:
        oa_role = 'OA is in active mode'
        command03a_resp = 'OA is Active'
        command03a_exit = 0
    
    # Wait for the command prompt before proceeding
    child.expect(COMMAND_PROMPT)
    
    # Send the results to Nagios
    print('%s' % (command03a_resp))
    sys.exit(command03a_exit)
    
    # Now exit the remote host.
    child.sendline('exit')
    
if __name__ == "__main__":
    main()
