# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import logging
import re
import splunk.admin as admin
from splunk.admin import ArgValidationException
from spp.config import EntityEndpoint, ConfigOption
from spp.java.bridge import executeBridgeCommand

logger = logging.getLogger('spp.dbx.dblookups')
logger.setLevel(logging.DEBUG)


class DatabaseLookupEntityEndpoint(EntityEndpoint):
    SUPPORTED_OPTIONS = (
        ConfigOption("database", mandatory=True),
        ConfigOption("table"),
        ConfigOption("fields", multiValue=True, multiValueCount=100),
        ConfigOption("advanced", mandatory=True),
        ConfigOption("input_fields", multiValue=True, multiValueCount=100),
        ConfigOption("query"),
        ConfigOption("max_matches")
    )

    CONFIG = "dblookup"

    def computeTransformsFields(self, props):
        fields = list()
        if 'fields' in props:
            for f in props['fields'].split(","):
                v = re.split(r'\s+', f.strip())[0]
                if v and not v in fields: fields.append(v)
        if 'input_fields' in props:
            for f in props['input_fields'].split(","):
                v = re.split(r'\s+', f.strip())[0]
                if v and not v in fields: fields.append(v)
        return fields

    def process_modification(self, id, props, type, output):
        if type == 'create':
            if self.callerArgs.id in self.readConf("transforms"):
                raise ArgValidationException("Transforms stanza [%s] already exists" % self.callerArgs.id)
        self.writeConf("transforms", self.callerArgs.id, {
            "external_cmd": "dblookup.py %s" % self.callerArgs.id,
            "fields_list": ",".join(self.computeTransformsFields(props))
        })
        self.reloadEndpoint("/data/transforms/lookups")
        return id, props

    def postModificationCallback(self):
        self.reloadDbLookups()

    def postRemoveCallback(self):
        self.reloadDbLookups()

    def reloadDbLookups(self):
        self.reloadEndpoint("/data/transforms/lookups")
        executeBridgeCommand("com.splunk.bridge.cmd.Reload", ["dblookup"], checkStatus=True)

    def handleRemove(self, output):
        EntityEndpoint.handleRemove(self, output)
        self.deleteConfStanza("transforms", self.callerArgs.id)
        self.reloadEndpoint("/data/transforms/lookups")

    def handleReload(self, confInfo):
        logger.debug("DBX dblookup reload called")


admin.init(DatabaseLookupEntityEndpoint, admin.CONTEXT_NONE)
