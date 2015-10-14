# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import sys
import signal
from spp.java import *
from spp.java.bridge import executeBridgeCommand

import logging

logging.basicConfig(level=logging.DEBUG,
                    filename=os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'jbridge.log'),
                    format='%(asctime)s %(levelname)s %(message)s', filemode='a')
logger = logging.getLogger('spp.dbx.javabridge')


def log(msg):
    logger.debug(msg)


try:
    executeBridgeCommand("com.splunk.bridge.cmd.Shutdown", checkStatus=True)
    log("JavaBridgeServer was still running...")
except:
    pass

java = JavaEnv()
OBSOLETE = ("jtds-1.2.jar")
logger.info("Checking for obsolete java libraries in %s", java.lib_path)
for file in os.listdir(java.lib_path):
    if file in OBSOLETE:
        logger.info("Deleting obsolete jar file %s", file)
        os.remove(os.path.join(java.lib_path, file))
logger.debug("Starting JavaBridgeServer...")
process = java.execute("com.splunk.bridge.JavaBridgeServer", [str(os.getpid())])
logger.info("Started JavaBridgeServer PID=%d", process.process.pid)


def signal_cleanup(s, f):
    cleanup()


def cleanup():
    log("cleanup callback... termingating process")
    try:
        log("sending shutdown command to jbridge server")
        executeBridgeCommand("com.splunk.bridge.cmd.Shutdown", checkStatus=True)
    except Exception, e:
        log("Error terminating process: %s" % e)
    try:
        log("terminating jbridge process")
        process.terminate()
    except:
        log("Error terminating jbridge process")
    log("termining wrapper process sys.exit(1)")
    sys.exit(1)


watcher = None
running = True

if os.name == 'nt':
    try:
        def win32sighandler(*args):
            logger.debug("WIN32 SIGNAL %s", args)
            cleanup()
            return True

        import win32api

        win32api.SetConsoleCtrlHandler(win32sighandler, True)
        logger.debug("win32 handler registered")
    except Exception, e:
        log.error("Error registering Win32 callback: %s", e)
else:
    signal.signal(signal.SIGTERM, signal_cleanup)

    if hasattr(os, 'uname') and os.uname()[0] == 'Linux':
        from threading import Thread
        import time

        class PPIDWatcher(Thread):
            def __init__(self):
                super(PPIDWatcher, self).__init__()

            def run(self):
                ppid = os.getppid()
                while running:
                    time.sleep(1)
                    try:
                        os.kill(ppid, 0)
                    except:
                        logger.warn("Parent process pid=%d vanished. Shutting down Javabridge Server.", ppid)
                        cleanup()
                        break

        log("starting pid watcher...")
        watcher = PPIDWatcher()
        watcher.start()

try:
    process.waitFor(checkReturnCode=True)
except Exception, e:
    log("Error waiting for process: %s" % e)
running = False
log("JavaBridgeServer terminated")
if watcher: watcher.join()
sys.exit(0)