# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import logging
import os
import splunk

import splunk.admin as admin
from splunk.util import normalizeBoolean
import spp
from spp.config import SetupEndpoint
from spp.java.bridge import executeBridgeCommand, CACHED_CFG_FILE

logger = logging.getLogger('spp.dbx.setup')
#logger.setLevel(logging.DEBUG)

class DBXSetupEndpoint(SetupEndpoint):
    CONFIG = "java"
    SUPPORTED_OPTIONS = {
        "bridge": ('addr', 'port', 'threads', 'debug'),
        "logging": ('level', 'file'),
        "persistence": ('global',),
        "output": ("default", "default.timestamp.format"),
        "config": ("adapter", "cache"),
        "dbx": ("database.factory", "database.factory.pooled", "pool.maxActive", "pool.maxIdle", "cache.tables",
                "cache.tables.size", "cache.tables.invalidation.timeout", "preload.config"),
        "dbmon": ("threads", "output.channel"),
        "dblookup": ("cache", "cache.size", "cache.invalidation.timeout"),
        "java": ('home', 'options')
    }

    def process_list(self, output):
        if not 'home' in output['java'] or not output['java']['home']:
            output['java']['home'] = spp.java.autodetect_java_home()

    def process_edit(self, output, props):
        id = self.callerArgs.id

        if id == 'java':
            try:
                version = spp.java.get_java_version(self.callerArgs.get("home", [None])[0],
                                                    overrideOpts=self.callerArgs.get("options", [None])[0])
                if not (version.getMajor() >= 1 and version.getMinor() >= 6):
                    raise admin.ArgValidationException, "Java Version is not compatible with DBX (JVM 1.6+ is required)"
            except Exception, e:
                raise admin.ArgValidationException, "The specified JAVA_HOME is invalid: %s" % e
            entity = splunk.entity.getEntity("/data/inputs/script", self.getJavaBridgeServerScript(), namespace="dbx",
                                             sessionKey=self.getSessionKey(), owner="nobody")
            script_disabled = normalizeBoolean(entity.get("disabled"))
            if script_disabled:
                logger.info("Enabling scripted input for java bridge server: %s", entity.getFullPath())
                splunk.entity.controlEntity("enable", "%s/enable" % entity.getFullPath(),
                                            sessionKey=self.getSessionKey())
            else:
                logger.debug("Script %s is already enabled", entity.getFullPath())
            if self.validateBatchInput():
                self.restartJavaBridgeServer()
        else:
            self.shouldReload = True

    def validateBatchInput(self):
        batchInputPath = os.path.join('$SPLUNK_HOME', 'var', 'spool', 'dbmon', '*.dbmonevt')
        try:
            batchInput = splunk.entity.getEntity('/data/inputs/monitor', batchInputPath, namespace='dbx',
                                                 sessionKey=self.getSessionKey(), owner="nobody")
            if normalizeBoolean(batchInput.get('disabled')):
                splunk.entity.controlEntity("enable", "%s/enable" % batchInput.getFullPath(),
                                            sessionKey=self.getSessionKey())
            return True
        except splunk.ResourceNotFound:
            self.createBatchInput(batchInputPath)
            return False

    def createBatchInput(self, batchInputPath):
        input = splunk.entity.Entity('/admin/conf-inputs', 'batch://%s' % batchInputPath, namespace='dbx',
                                     owner='nobody')
        input['sourcetype'] = 'dbmon:spool'
        input['move_policy'] = "sinkhole"
        input['crcSalt'] = "<SOURCE>"
        input['disabled'] = "0"
        splunk.entity.setEntity(input, sessionKey=self.getSessionKey())
        splunk.entity.refreshEntities('/admin/monitor', sessionKey=self.getSessionKey())

    def getJavaBridgeServerScript(self):
        return os.path.join("$SPLUNK_HOME", "etc", "apps", "dbx", "bin", "jbridge_server.py")

    def restartJavaBridgeServer(self):
        logger.debug("Restarting java bridge server after processing stanza [%s] with callerArgs: %s",
                     self.callerArgs.id, self.callerArgs)
        try:
            executeBridgeCommand("com.splunk.bridge.cmd.Shutdown", checkStatus=True)
        except Exception, e:
            logger.debug("Error sending shutdown command to bridge server: %s", e)
        self.handleReload(None)

    def handleReload(self, confInfo):
        logger.debug("DBX DBXSetupEndpoint reload called")
        if os.path.exists(CACHED_CFG_FILE): os.remove(CACHED_CFG_FILE)


admin.init(DBXSetupEndpoint, admin.CONTEXT_NONE)