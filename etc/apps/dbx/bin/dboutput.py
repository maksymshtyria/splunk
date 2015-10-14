# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import os
import sys
from spp.java.bridge import JavaBridge, JavaBridgeError
from splunk import Intersplunk as si

#(isInfo, sys.argv) = si.isGetInfo(sys.argv)
#keywords = sys.argv[1:]
#if isInfo:
#	si.outputInfo(
#		streaming = True,
#		generating = False,
#		retevs = True,
#		reqsop = False,
#		preop = None,
#		timeorder = False,
#		req_fields = "*"
#	)

stdin = None
if not os.isatty(0):
    stdin = sys.stdin

try:
    sys.exit(JavaBridge(stdin=stdin).execute("com.splunk.dbx.command.output.DatabaseOutputCommand", *sys.argv[1:]))
except JavaBridgeError, e:
    print 'ERROR\n"%s"' % e