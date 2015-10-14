# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
from StringIO import StringIO
import os
from spp.java.bridge import JavaBridge
from splunk.clilib import cli_common as cli
from subprocess import *


def normalize_path(path):
    return os.path.expandvars(os.path.join(*path.split("/")))


def encrypt_config_value(value):
    out = StringIO()
    bc = JavaBridge(stdout=out, stderr=None)
    bc.execute("com.splunk.config.crypt.Crypt", "encrypt", value)
    return out.getvalue().strip()


def decrypt_config_value(value):
    out = StringIO()
    bc = JavaBridge(stdout=out, stderr=None)
    bc.execute("com.splunk.config.crypt.Crypt", "decrypt", value)
    return out.getvalue().strip()


def getConfInContext(confName, app, user=None):
    cmd = ['btool', confName, 'list']
    if app: cmd.append('--app=%s' % app)
    if user: cmd.append('--user=%s' % user)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out = p.communicate()[0]
    return cli.readConfLines(out.splitlines())


def quote_str(str):
    if str is None: return ""
    str = repr(str)
    return str[1:len(str) - 1]


def escape_str(str):
    if str:
        return str.replace('\\', '\\\\').replace('\r', '\\r').replace('\n', '\\n')
    else:
        return str


def unescape_str(str):
    if str:
        return str.replace('\\r', '\r').replace('\\n', '\n').replace('\\\\', '\\')
    else:
        return str
