#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-
# 
# Script for checking the network configuration on Ericsson MSP servers and
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
# python check_msp_ifconfig.py [-H hostname] [-A ipaddress] [-U username] [-P password]
#     -H <hostname>               Remote server's hostname
#     -A <ipaddress>              Remote server's IP address
#     -U <username>               SSH username for the Remote server
#     -P <password>               SSH password for the Remote server
# 
# 

from __future__ import absolute_import
import csv
import datetime
import getopt
import os
import pexpect
import re
import string
import sys
import time
from time import gmtime, strftime
from datetime import date, datetime


def exit_with_usage():

    print(globals()['__doc__'])
    os._exit(1)

def main():
    
    ######################################################################
    ## Parse the options, arguments, get ready, etc.
    ######################################################################
    
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'h?H:A:U:P:', ['help','h','?'])
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
    
    # Some constants
    # This is the prompt we get if SSH does not have the remote host's public key stored in the cache.
    SSH_NEWKEY = '[Aa]re you sure you want to continue connecting \(yes/no\)\?'
    CONN_REFUSED = 'Connection refused'
    #COMMAND_PROMPT = '~\]\#\s' # use this when testing as root
    # sample command prompt: hostname02msp1ai01:~> 
    COMMAND_PROMPT = hostname + ':~>\s'
    
    # Set variables
    critical = 5000.0
    warning = 3000.0
    
    # SSH to server
    child = pexpect.spawn('/usr/bin/ssh %s@%s' % (username, ipaddress))
    
    # uncomment the following line for debugging
    #child.logfile = sys.stdout
    
    i = child.expect([CONN_REFUSED, pexpect.TIMEOUT, SSH_NEWKEY, COMMAND_PROMPT, '(?i)password'], timeout=2)
    if i == 0: # Connection refused
        command_resp = 'CRITICAL: connection refused'
        command_exit = 2
        print('%s' % (command_resp))
        sys.exit('command_exit')
        # Now exit the remote host.
        child.sendline('exit')
    if i == 1: # Timeout
        command_resp =('CRITICAL: could not login with SSH.')
        command_exit = 2
        print('%s' % (command_resp))
        sys.exit('command_exit')
        # Now exit the remote host.
        child.sendline('exit')
    if i == 2: # In this case SSH does not have the public key cached.
        child.sendline('yes')
        child.expect('(?i)password')
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
        i = child.expect(['[Pp]assword: ', COMMAND_PROMPT])
        if i == 0:
            # password prompt again, probably because the password was not accepted
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
    
    if 'hostname02mspadm' in hostname or 'hostname04mspadm' in hostname or 'hostname05mspadm' in hostname:
        command03_expect = 8
    if 'hostname03mspadm' in hostname:
        command03_expect = 8
    if 'hostname02msp1da' in hostname or 'hostname02msp2da' in hostname:
        command03_expect = 8
    if 'hostname03msp1da' in hostname or 'hostname03msp2da' in hostname:
        command03_expect = 8
    if 'hostname04msp1da' in hostname or 'hostname04msp2da' in hostname:
        command03_expect = 8
    if 'hostname05msp1da' in hostname or 'hostname05msp2da' in hostname:
        command03_expect = 8
    if 'msp1ddc' in hostname or 'msp2ddc' in hostname:
        command03_expect = 7
    if 'hostname02mspmn' in hostname or 'hostname03mspmn' in hostname:
        command03_expect = 9
    if 'hostname04mspmn' in hostname:
        command03_expect = 9
    if 'hostname05mspmn' in hostname:
        command03_expect = 6
    if 'hostname02mspmon' in hostname:
        command03_expect = 8
    if 'hostname03mspmon' in hostname or 'hostname04mspmon' in hostname or 'hostname05mspmon' in hostname:
        command03_expect = 8
    if 'hostname02msp1ts' in hostname:
        command03_expect = 14
    if 'hostname03msp1ts' in hostname or 'hostname04msp1ts' in hostname or 'hostname05msp1ts' in hostname:
        command03_expect = 15
    if 'mspvmt' in hostname:
        command03_expect = 6
    if 'hostname05' in hostname or 'mspvmt' in hostname:
        command03_cmd = '/sbin/ifconfig -a'
    else:
        command03_cmd = 'sudo ifconfig -a'
        
    # Issue command via ssh
    child.sendline('%s' % (command03_cmd))
    
    # Wait for the command prompt before proceeding
    i = child.expect([COMMAND_PROMPT, 'root.s\spassword:', pexpect.TIMEOUT])
    if i == 0:
        # Read ssh response, post-process and write data to the csv file
        command03_tmp = child.before
        command03_cnt = command03_tmp.count(' UP BROADCAST ')
        if command03_cnt == command03_expect:
            command03_resp = 'OK: %s interfaces UP' % (command03_cnt)
            command03_exit = 0
        else:
            command03_resp = 'WARNING: %s interfaces UP' % (command03_cnt)
            command03_exit = 1
    if i == 1:
        child.send('\003')
        child.expect(COMMAND_PROMPT)
        command03_resp = 'Command failed'
        command03_tmp = 'Requires root password'
        command03_exit = 2
    
    # Send the results to Nagios
    print('%s | %s' % (command03_resp,command03_tmp))
    sys.exit(command03_exit)
    
    # Now exit the remote host.
    child.sendline ('exit')
    
if __name__ == "__main__":
    main()
