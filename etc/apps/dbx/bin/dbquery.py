# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import sys
from spp.java.bridge import JavaBridge, JavaBridgeError

try:
    sys.exit(JavaBridge(stdin=sys.stdin).execute("com.splunk.dbx.command.DatabaseQueryCommand", *sys.argv[1:]))
except JavaBridgeError, e:
    print 'ERROR\n"%s"' % e