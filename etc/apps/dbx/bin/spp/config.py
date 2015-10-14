# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import logging
from splunk.admin import BadProgrammerException
import splunk.entity
import splunk.bundle
import splunk.admin
import splunk.rest

logger = logging.getLogger('spp.config')
logger.setLevel(logging.DEBUG)


class ConfigEndpoint(splunk.admin.MConfigHandler):
    """Custom abstract subclass of MConfigHandler which implements a few utility methods"""

    def deleteConfStanza(self, conf, stanza):
        cfg = self.readConfCtx(conf)
        if stanza in cfg:
            cfg = cfg[stanza]
            sessionKey = self.getSessionKey()
            entity = splunk.entity.getEntity("/admin/conf-%s" % conf, stanza, sessionKey=sessionKey, owner='nobody',
                                             namespace=cfg['eai:appName'])
            splunk.entity.deleteEntity('/admin/conf-%s' % conf, stanza, entity['eai:acl']['app'], owner='nobody',
                                       sessionKey=sessionKey)

    def reloadEndpoint(self, endpoint):
        splunk.rest.simpleRequest("%s/_reload" % endpoint, method="POST", postargs=dict(),
                                  sessionKey=self.getSessionKey())

    def _get_arg(self, name, defVal=None):
        return self.callerArgs.get(name, [defVal])[0]


class ConfigOption:
    DEFAULT = 0
    READONLY = 1
    WRITEONLY = 2
    MANDATORY = 4
    TRANSIENT = 8
    MULTIVALUE = 16

    def __init__(self, name, readonly=False, writeonly=False, mandatory=False, defaultValue=None, transient=False,
                 multiValue=False, multiValueCount=10, multiValueStoredIndexed=False, createonly=False):
        self.name = name
        self.readonly = readonly
        self.writeonly = writeonly
        self.mandatory = mandatory
        self.transient = transient
        self.defaultValue = defaultValue
        self.multiValue = multiValue
        self.multiValueCount = multiValueCount
        self.multiValueStoredIndexed = multiValueStoredIndexed
        self.createonly = createonly

    def __str__(self):
        flags = []
        for attr in ["multiValue", "readonly", "writeonly", "mandatory", "transient", "defaultValue", "createonly"]:
            if getattr(self, attr): flags.append(attr.upper())
        return "Option{ name=%s %s }" % (self.name, " ".join(flags))


def createConfigOption(arg):
    if isinstance(arg, ConfigOption):
        return arg
    elif type(arg) in (tuple, list):
        name = arg[0]
        params = {}
        if len(arg) > 1:
            flags = arg[1]
            if flags & ConfigOption.READONLY: params['readonly'] = True
            if flags & ConfigOption.WRITEONLY == ConfigOption.WRITEONLY: params['writeonly'] = True
            if flags & ConfigOption.MANDATORY == ConfigOption.MANDATORY: params['mandatory'] = True
            if flags & ConfigOption.TRANSIENT == ConfigOption.TRANSIENT: params['transient'] = True
            if flags & ConfigOption.MULTIVALUE == ConfigOption.MULTIVALUE: params['multiValue'] = True
        if len(arg) > 2:
            params['defaultValue'] = arg[2]
        return ConfigOption(name, **params)
    elif type(arg) is str:
        return ConfigOption(arg)
    else:
        raise BadProgrammerException("Invalid type of SUPPORTED_OPTIONS entry %s" % type(arg))


DBG_ACTIONS = {
1: "CREATE",
2: "LIST",
4: "EDIT",
8: "REMOVE",
16: "MEMBERS",
32: "RELOAD"
}


class EntityEndpoint(ConfigEndpoint):
    SUPPORTED_OPTIONS = None
    CONFIG = None

    DEBUG = False

    def __init__(self, scriptMode, ctxInfo):
        splunk.admin.MConfigHandler.__init__(self, scriptMode, ctxInfo)
        if self.DEBUG: logger.debug("%s INIT %s, %s [%s]", self.__class__.__name__, scriptMode,
                                    self.requestedAction in DBG_ACTIONS and DBG_ACTIONS[
                                        self.requestedAction] or self.requestedAction, self.callerArgs.id)
        self._setup_supported_options()

    def _inspect_callerArgs(self):
        logger.debug("callerArgs: %s", self.callerArgs)

    def _setup_supported_options(self):
        options = self.SUPPORTED_OPTIONS
        opt = []
        for item in options:
            opt.append(createConfigOption(item))
        self._supported_options = tuple(opt)

    def setup(self):
        if self.requestedAction in (splunk.admin.ACTION_EDIT, splunk.admin.ACTION_CREATE):
            for opt in self._supported_options:
                if opt.multiValue:
                    self.supportedArgs.addOptArg("%s." % opt.name)
                    if self.requestedAction == splunk.admin.ACTION_EDIT:
                        for i in range(opt.multiValueCount):
                            self.supportedArgs.addOptArg("%s.%d" % (opt.name, i))
                else:
                    if (not opt.createonly) or self.requestedAction == splunk.admin.ACTION_CREATE:
                        if opt.mandatory:
                            self.supportedArgs.addReqArg(opt.name)
                        else:
                            self.supportedArgs.addOptArg(opt.name)

    def _getConfigItems(self):
        return self.readConfCtx(self.CONFIG)

    def handleList(self, output):
        config = self._getConfigItems()
        for name, settings in config.items():
            for opt in self._supported_options:
                if not opt.writeonly:
                    if opt.multiValue:
                        values = []
                        if opt.multiValueStoredIndexed:
                            raise Exception("multiValueStoredIndexed not implemented")
                        else:
                            list = settings.get(opt.name, "")
                            if list:
                                values = [x.strip() for x in list.split(",") if x]
                        output[name].append(opt.name, ", ".join(values))
                        for i, v in enumerate(values):
                            output[name].append('%s.%d' % (opt.name, i), v)
                    else:
                        value = settings.get(opt.name, opt.defaultValue)
                        if hasattr(self, 'process_list_%s' % opt.name):
                            value = getattr(self, 'process_list_%s' % opt.name)(opt, value, output=output,
                                                                                stanza=settings,
                                                                                config=config)
                        output[name].append(opt.name, value)
        self.process_list(output)

    #logger.debug("EntityEndpoint.handleList => OUTPUT %s" % output)

    def process_list(self, output):
        pass

    def handleModification(self, type, output):
        #logger.debug("EntityEndpoint handling modification type=%s", type)
        id = self.callerArgs.id
        if id:
            props = {}
            for opt in self._supported_options:
                if opt.multiValue:
                    #logger.debug("Handling multivalue property %s", opt.name)
                    value = []
                    for i in range(opt.multiValueCount):
                        p = '%s.%d' % (opt.name, i)
                        if p in self.callerArgs:
                            value += [x.strip() for x in self.callerArgs[p] if x]
                    if '%s.' % opt.name in self.callerArgs:
                        value += [x.strip() for x in self.callerArgs['%s.' % opt.name] if x]

                else:
                    value = self._get_arg(opt.name, opt.defaultValue)
                m = "process_modify_%s" % opt.name
                if hasattr(self, m):
                    value = getattr(self, m)(value, modifyType=type)
                m = "process_%s_%s" % (type, opt.name)
                if hasattr(self, m):
                    value = getattr(self, m)(value)
                if not opt.transient:
                    if value is not None:
                        if opt.multiValue:
                            if opt.multiValueStoredIndexed:
                                raise Exception("multiValueStoredIndexed not implemented")
                            #								for i, v in enumerate(value):
                            #									props['%s.%d' % (opt.name, i)] = v
                            else:
                                props[opt.name] = ",".join(value)
                        else:
                            props[opt.name] = value
                        #				else:
                        #					logger.debug("Option %s is transient" % opt.name)
            id, props = self.process_modification(id, props, type=type, output=output)
            #logger.debug("Storing properties: %s: %s" % (id,props))
            self.writeConf(self.CONFIG, id, props)
            self.postConfUpdate(id, props)

    def postConfUpdate(self, id, props):
        pass

    def process_modification(self, id, props, type, output):
        return id, props

    def handleCreate(self, output):
        self.handleModification("create", output)
        self.postCreateCallback()

    def postCreateCallback(self):
        self.postModificationCallback()

    def handleEdit(self, output):
        self.adjustNamespace()
        self.handleModification("edit", output)
        self.postEditCallback()

    def adjustNamespace(self):
        import splunk.entity as en
        entity = en.getEntity('configs/conf-%s' % self.CONFIG, self.callerArgs.id,
                              sessionKey=self.getSessionKey(), namespace='-', owner='-')
        self.appName = entity['eai:acl']['app']

    def postEditCallback(self):
        self.postModificationCallback()

    def handleRemove(self, output):
        id = self.callerArgs.id
        if id:
            self.deleteConfStanza(self.CONFIG, id)
        #self.shouldReload = True
        self.postRemoveCallback()

    def postRemoveCallback(self):
        self.shouldReload = True
        self.postModificationCallback()

    def postModificationCallback(self):
        pass


class SetupEndpoint(ConfigEndpoint):
    SUPPORTED_OPTIONS = None

    CONFIG = None

    def __init__(self, *args, **kvargs):
        splunk.admin.MConfigHandler.__init__(self, *args, **kvargs)
        self._setup_supported_options()

    def _setup_supported_options(self):
        options = self.SUPPORTED_OPTIONS
        opt = {}
        for stanza, items in options.items():
            l = list()
            for item in items:
                if type(item) is str:
                    l.append(ConfigOption(item))
                elif type(item) is tuple or type(item) is list:
                    name = item[0]
                    if len(item) > 1:
                        flags = item[1]
                        flag_dict = {}
                        if flags & ConfigOption.READONLY: flag_dict['readonly'] = True
                        if flags == ConfigOption.WRITEONLY: flag_dict['writeonly'] = True
                        if flags == ConfigOption.MANDATORY: flag_dict['mandatory'] = True
                        l.append(ConfigOption(name, **flag_dict))
                    else:
                        l.append(ConfigOption(name))
                else:
                    pass
            opt[stanza] = l
        self._supported_options = opt

    def setup(self):
        if self.callerArgs.id and self.callerArgs.id in self._supported_options:
            for opt in self._supported_options[self.callerArgs.id]:
                if opt.mandatory:
                    self.supportedArgs.addReqArg(opt.name)
                else:
                    self.supportedArgs.addOptArg(opt.name)
        else:
            for x, opts in self._supported_options.items():
                for opt in opts:
                    if opt.mandatory:
                        self.supportedArgs.addReqArg(opt.name)
                    else:
                        self.supportedArgs.addOptArg(opt.name)

    def handleList(self, output):
        config = self.readConfCtx(self.CONFIG)
        for stanza, opts in self._supported_options.items():
            cfg = config[stanza]
            for opt in opts:
                if not opt.writeonly:
                    output[stanza].append(opt.name, cfg.get(opt.name))
        self.process_list(output)

    def process_list(self, output):
        pass

    def handleEdit(self, output):
        props = {}
        for arg in self._supported_options[self.callerArgs.id]:
            if not arg.readonly:
                props[arg.name] = self.callerArgs.get(arg.name, [None])[0]
        self.process_edit(output, props)
        self.writeConf(self.CONFIG, self.callerArgs.id, props)

    def process_edit(self, output, props):
        return props