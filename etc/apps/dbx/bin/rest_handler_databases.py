# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.

import splunk.admin as admin
from splunk.util import normalizeBoolean
import logging, spp, spp.config
from spp.config import EntityEndpoint, ConfigOption
from spp.java.bridge import executeBridgeCommand

logger = logging.getLogger('spp.dbx.databases')
logger.setLevel(logging.DEBUG)


class DatabaseEntityEndpoint(EntityEndpoint):
    SUPPORTED_OPTIONS = (
        ConfigOption('type', mandatory=True),
        ConfigOption('host', mandatory=True),
        ConfigOption('port'),
        ConfigOption('database', mandatory=True),
        ConfigOption('username'),
        ConfigOption('password', writeonly=True),
        ConfigOption('readonly', defaultValue="1"),
        ConfigOption("validate", writeonly=True, transient=True),
        ConfigOption("disabled")
    )
    CONFIG = 'database'

    def process_modify_password(self, val, modifyType=None):
        if val:
            return spp.util.encrypt_config_value(val)

    def process_modification(self, id, props, type, output):
        if normalizeBoolean(self._get_arg("validate")):
            logger.debug("Validating database connection")
            id = self.callerArgs.id
            curCfg = self.readConf(self.CONFIG)
            if curCfg and id in curCfg:
                curCfg = curCfg[id]
            else:
                curCfg = {}
            logger.debug("Read current db configuration %s", curCfg)
            logger.debug("Merging new parameters: %s", props)
            curCfg.update(props)
            logger.debug("Merged changed. Config to validate: %s", curCfg)
            validation_args = []
            for k, v in curCfg.items():
                validation_args.append("%s=%s" % (k, v if v is not None else ''))
            logger.debug("Executing database validate: com.splunk.dbx.sql.validate.DatabaseValidator %s",
                         " ".join(validation_args))
            (ret, out, err) = executeBridgeCommand("com.splunk.dbx.sql.validate.DatabaseValidator", args=validation_args
                , fetchOutput=True)
            logger.debug("Validation result: %s", ret)
            if not ret is 0:
                raise admin.ArgValidationException(
                    out and out.strip() or "Unknown error while validating database connection")
        return id, props

    def postModificationCallback(self):
        executeBridgeCommand("com.splunk.bridge.cmd.Reload", args=["databases"], checkStatus=True)

    def handleReload(self, confInfo):
        logger.debug("DBX databases reload called")
        executeBridgeCommand("com.splunk.bridge.cmd.Reload", args=["databases"], checkStatus=True)

    def setDisabled(self, id, disabled):
        self.writeConf(self.CONFIG, id, {"disabled": disabled})
        self.postModificationCallback()

    def handleCustom(self, confInfo):
        logger.debug("CUSTOM %s action=%s" % (self.callerArgs.id, self.customAction))

        if self.customAction == 'disable':
            self.setDisabled(self.callerArgs.id, '1')
        elif self.customAction == 'enable':
            self.setDisabled(self.callerArgs.id, '0')
        else:
            MConfigHandler.handleCustom(self, confInfo)


admin.init(DatabaseEntityEndpoint, admin.CONTEXT_NONE)