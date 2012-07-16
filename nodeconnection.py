#!/usr/bin/env python

import argparse
import getpass
from noderange import expand
import io
import os
import paramiko
from paramiko import SSHException
import string
import select
import sys

class NodeConnection(object):
    _password = None
    def __init__(self, name, user=None, password=None):
        self.name = name
        self.ssh = None
        self.stdin = None
        self.stdout = None
        self.stderr = None
        if user:
            self._user = user
        else:
            self._user = getpass.getuser()
        if not password is None:
            NodeConnection._password = password

    def connect(self, verbose=False, port=22):
        if verbose:
        	print "Connection to host '%s'" % (self.name)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.name, 22, self._user,
                             password=NodeConnection._password)
        except SSHException as e:
            #Try again with a password
            NodeConnection._password = \
                    getpass.getpass("Key based logon did not work, please "
                                    "provide password for  %s@%s: " %
                                    (self._user, self.name), stream=sys.stderr)
            self.ssh.connect(self.name, 22, self._user,
                             password=NodeConnection._password)

    def exec_command(self, cmd):
        if not self.ssh:
        	raise Exception("exec_command: not connected")
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command(cmd)

    def exec_sudo_command(self, cmd):
        self.stdout = io.StringIO()
        self.stdin = io.StringIO()
        self.stderr = io.StringIO()
        chan = self.ssh.get_transport().open_session()
        chan.get_pty()
        chan.exec_command(cmd)
        prompt = chan.recv(1024)
        if string.find(prompt, "password") != -1:
            if NodeConnection._password is None:
                NodeConnection._password = getpass.getpass(
                                    "Sudo access requires a password, please"
                                    " provide password for  %s@%s: " %
                                    (self._user, self.name), stream=sys.stderr)
            plen = chan.send(NodeConnection._password + '\n')
            data = chan.recv(1024)
            while chan.exit_status_ready() != True:
                rl, wl, xl = select.select([chan],[],[],0.0)
                data += chan.recv(1024)
            self.stdout = io.StringIO(unicode(data))
        else:
            self.stdout = io.StringIO(unicode(prompt))

    def print_output(self, leader='', output=False):
        #FIXME: dshbak (leader) mode nott yet implemented correctly due to
        #       readline() returning a character at a time rather than a line.
        outbuf = []
        if not self.stdin or not self.stdout or not self.stderr:
        	raise Exception("print_output: not connected")
        for line in self.stdout.readlines():
            if output is True:
                outbuf.append(line)
            else:
                sys.stdout.write(line)
        sys.stdout.flush()
        for line in self.stderr.readlines():
            if output is True:
                outbuf.append(line)
            else:
                sys.stderr.write(line)
        sys.stderr.flush()
        if output:
            return outbuf

def runonnodes(nodespec, cmd, dshbak=False, verbose=False,
               user=None, password=None, output=False,
               sudo=False):
    nodes = expand(nodespec)

    if len(nodes) == 0:
        print "Need at least one node to run on"
        sys.exit(1)

    for node in nodes:
        nc = NodeConnection(node, user, password)
        nc.connect(verbose=verbose)
        if sudo is False:
            nc.exec_command(cmd)
        else:
            nc.exec_sudo_command(cmd)
        if not dshbak:
            print "--------------- %s ---------------" % (node)
            outbuf = nc.print_output(output=output)
        else:
            outbuf = nc.print_output(str(node) + ": ", output=output)
    if output == True:
        return outbuf
