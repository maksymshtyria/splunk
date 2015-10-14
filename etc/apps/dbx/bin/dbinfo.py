# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import os
import sys
from spp.java.bridge import JavaBridge, JavaBridgeError
from splunk import Intersplunk as si

(isInfo, sys.argv) = si.isGetInfo(sys.argv)
keywords = sys.argv[1:]

if isInfo:
    # TODO: Parameter validation
    si.outputInfo(False, True, False, False, None, False)

stdin = None
if not os.isatty(0):
    stdin = sys.stdin

try:
    sys.exit(JavaBridge(stdin=stdin).execute("com.splunk.dbx.command.DatabaseInfoCommand", *sys.argv[1:]))
except JavaBridgeError, e:
    print 'ERROR\n"%s"' % e