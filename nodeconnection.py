#!/usr/bin/env python

import argparse
import getpass
from noderange import expand
import os
import paramiko
from paramiko import SSHException
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

    def print_output(self, leader=''):
        #FIXME: dshbak (leader) mode nott yet implemented correctly due to
        #       readline() returning a character at a time rather than a line.
        if not self.stdin or not self.stdout or not self.stderr:
        	raise Exception("print_output: not connected")
        for line in self.stdout.readlines():
            sys.stdout.write(line)
        sys.stdout.flush()
        for line in self.stderr.readlines():
        	sys.stderr.write(line)
        sys.stderr.flush()

def runonnodes(nodespec, cmd, dshbak=False, verbose=False,
               user=None, password=None):
    nodes = expand(nodespec)

    if len(nodes) == 0:
        print "Need at least one node to run on"
        sys.exit(1)

    for node in nodes:
        nc = NodeConnection(node, user, password)
        nc.connect(verbose=verbose)
        nc.exec_command(cmd)
        if not dshbak:
            print "--------------- %s ---------------" % (node)
            nc.print_output()
        else:
            nc.print_output(str(node) + ": ")

