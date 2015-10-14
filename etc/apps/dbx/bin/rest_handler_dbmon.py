# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import logging
import re
from splunk import admin
from splunk.admin import MConfigHandler
from spp.config import EntityEndpoint, ConfigOption
import splunk.entity as en
from spp.java.bridge import executeBridgeCommand
from spp.util import escape_str, unescape_str

logger = logging.getLogger('spp.dbx.dbmon')
logger.setLevel(logging.DEBUG)


class DatabaseMonitorEntityEndpoint(EntityEndpoint):
    SUPPORTED_OPTIONS = (
        ConfigOption("type", createonly=True, mandatory=True),
        ConfigOption("database", createonly=True, mandatory=True),
        ConfigOption("sourcetype"),
        ConfigOption("source"),
        ConfigOption("host"),
        ConfigOption("index"),
        ConfigOption("interval"),
        ConfigOption("query"),
        ConfigOption("table"),
        ConfigOption("output.format", mandatory=True),
        ConfigOption("output.timestamp"),
        ConfigOption("output.timestamp.column"),
        ConfigOption("output.timestamp.parse.format"),
        ConfigOption("output.timestamp.format"),
        ConfigOption("output.template"),
        ConfigOption("tail.rising.column"),
        ConfigOption("tail.follow.only"),
        ConfigOption("change.hash.algorithm"),
        ConfigOption("disabled")
    )

    CONFIG = 'inputs'

    TYPES = ('tail', 'dump', 'change', 'batch')

    ESCAPED_OPTIONS = ('output.template', 'query', 'query.initial')

    def _getConfigItems(self):
        result = {}
        thing = en.getEntities("configs/conf-inputs", sessionKey=self.getSessionKey(), namespace="-", owner="-",
                               count=-1, search="dbmon-")
        for s in thing:
            if s.startswith("dbmon-"):
                result[s] = {}
                result[s].update(thing[s].items())
        return result

    def parse_stanza(self, stanza):
        m = re.match(r'dbmon-(\w+)://([^/]+)/([^/]+)', stanza)
        return m.group(1), m.group(2), m.group(3)

    def process_list(self, output):
        #logger.debug("process_list %s", output)
        for stanza, props in output.items():
            monType, database, name = self.parse_stanza(stanza)
            props['database'] = database
            props['type'] = monType
            if not 'table' in props or not props['table']:
                props['table'] = name
            if not 'interval' in props or not props['interval']:
                props['interval'] = 'auto'
            for p in self.ESCAPED_OPTIONS:
                if p in props and props[p]:
                    props[p] = unescape_str(props[p])
                    #			if 'output.template' in props and props['output.template']:
                    #				props['output.template'] = unescape_str(props['output.template'])

        return output

    def process_modification(self, id, props, type, output):
        logger.debug("MODIFICATION %s => %s" % (id, props))
        if type == 'create':
            stanza = "dbmon-%s://%s/%s" % (props.get("type"), props.get("database"), id)
            logger.debug("STANZA %s", stanza)
            del props['type']
            del props['database']
        else:
            stanza = id
        if not 'query' in props:
            props['query'] = ''
        for p in self.ESCAPED_OPTIONS:
            if p in props and props[p]:
                props[p] = escape_str(props[p])
                #		if 'output.template' in props and props['output.template']:
                #			props['output.template'] = escape_str(props['output.template'])

        return stanza, props

    def setDisabled(self, id, disabled):
        self.writeConf(self.CONFIG, id, {"disabled": disabled})
        self.updateMonitor(id)

    def postConfUpdate(self, id, props):
        self.updateMonitor(id)

    def postRemoveCallback(self):
        self.updateMonitor(self.callerArgs.id)

    def handleCustom(self, confInfo):
        logger.debug("CUSTOM %s action=%s" % (self.callerArgs.id, self.customAction))

        if self.customAction == 'disable':
            self.setDisabled(self.callerArgs.id, '1')
        elif self.customAction == 'enable':
            self.setDisabled(self.callerArgs.id, '0')
        else:
            MConfigHandler.handleCustom(self, confInfo)

    def updateMonitor(self, stanza):
        executeBridgeCommand("com.splunk.bridge.cmd.Reload", ["dbmon", stanza], checkStatus=True)

    def validateConfig(self, id, cfg):
        args = [id]
        for k, v in cfg.items():
            args.append("%s=%s" % (k, v))
        executeBridgeCommand("com.splunk.dbx.monitor.DatabaseMonitorValidator", args, checkStatus=True)

    def handleReload(self, confInfo):
        logger.debug("DBX dbmon reload called")
        executeBridgeCommand("com.splunk.bridge.cmd.Reload", ["dbmon", "scheduler"], checkStatus=True)


admin.init(DatabaseMonitorEntityEndpoint, admin.CONTEXT_NONE)
