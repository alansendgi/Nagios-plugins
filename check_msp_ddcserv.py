#!/usr/local/bin/python2.7
# -*- coding: UTF-8 -*-
# 
# Script for checking the state of a Ericsson MSP DDC server and
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
# python check_msp_ddcserv.py [-H hostname] [-A ipaddress] [-U username] [-P password]
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
    # sample command prompt: user@hostnamemsp1ai01:~> 
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
    
    child.sendline('/opt/miep/tools/ddc_tool processinfo serv')
    
    # Wait for the command prompt before proceeding
    child.expect(COMMAND_PROMPT)
    
    # Read ssh response, post-process and write data to the csv file
    command11_tmp = child.before
    command11_cnt = command11_tmp.count('OK')
    
    if command11_cnt == 8:
        command11_resp = 'OK: %s DDC Server States OK' % (command11_cnt)
        command11_exit = 0
    if command11_cnt == 7:
        command11_resp = 'WARNING: %s DDC Server States OK' % (command11_cnt)
        command11_exit = 1
    if command11_cnt < 7:
        command11_resp = 'CRITICAL: %s DDC Server States OK' % (command11_cnt)
        command11_exit = 2
    
    
    # Send the results to Nagios
    ##################################################################
    print('%s | %s' % (command11_resp, command11_tmp))
    sys.exit(command11_exit)
    
    # Now exit the remote host.
    child.sendline ('exit')
    
if __name__ == "__main__":
    main()
