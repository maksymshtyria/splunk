# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import os
import sys
from spp.java.bridge import JavaBridge, JavaBridgeError

from splunk import Intersplunk as si

(isInfo, sys.argv) = si.isGetInfo(sys.argv)
keywords = sys.argv[1:]

if isInfo:
    si.outputInfo(False, True, True, False, None, False)

stdin = None
if not os.isatty(0):
    stdin = sys.stdin

try:
    sys.exit(JavaBridge(stdin=stdin).execute("com.splunk.dbx.monitor.Preview", *keywords))
except JavaBridgeError, e:
    print 'ERROR\n"%s"' % e