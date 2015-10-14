# Copyright (C) 2005-2013 Splunk Inc. All Rights Reserved.
import os, re
from subprocess import *
import shlex
from splunk.util import normalizeBoolean
import logging
from spp.util import getConfInContext

logger = logging.getLogger("spp.java")
DEFAULT_APP = "dbx"

REQUIRED_MAJOR_VERSION = 1
REQUIRED_MINOR_VERSION = 5


class JavaVersionException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class JavaExecutionException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class JavaVersion:
    def __init__(self, str):
        self.str = str
        self.parts = str.split(".")

    def getMajor(self):
        return int(self.parts[0])

    def getMinor(self):
        return int(self.parts[1])

    def is_compatible(self):
        return self.getMajor() > REQUIRED_MAJOR_VERSION and self.getMinor() > REQUIRED_MINOR_VERSION

    def __str__(self):
        return self.str


class JavaEnv:
    def __init__(self, app=DEFAULT_APP, cfg_name='java', cfg_stanza='java', java_home=None):
        logger.debug("Setting up Java Environment: app=%s, cfg_name=%s, cfg_stanza=%s, java_home=%s" % (
        app, cfg_name, cfg_stanza, java_home))
        self.lib_path = os.path.expandvars(
            os.path.join(os.path.normpath(os.path.join(__file__, '..', '..', '..')), 'lib'))
        self.app = app
        self.config = getConfInContext(cfg_name, app)
        JAVA_HOME = None
        java_cfg = self.config[cfg_stanza]
        if java_home:
            JAVA_HOME = java_home
        elif 'home' in java_cfg:
            JAVA_HOME = java_cfg['home']
        if not JAVA_HOME:
            JAVA_HOME = autodetect_java_home()
        if not os.path.exists(JAVA_HOME):
            raise JavaVersionException("JAVA_HOME directory %s does not exist" % JAVA_HOME)
        self.java_home = JAVA_HOME
        logger.debug("JAVA_HOME=%s", self.java_home)
        if 'options' in java_cfg:
            self.options = shlex.split(java_cfg['options'])
        else:
            self.options = []
        self.options.append('-Dsplunk.app.ctx=%s' % app)

        if normalizeBoolean(java_cfg.get("remote_debug", "false")):
            logger.debug("Remote debugging is enabled")
            dbg_host = java_cfg.get("remote_debug_host", "localhost")
            dbg_port = java_cfg.get("remote_debug_port", "5005")
            self.options.append("-Xdebug")
            self.options.append("-Xrunjdwp:transport=dt_socket,server=n,address=%s:%s,suspend=y" % (dbg_host, dbg_port))
        logger.debug("options=%s", str(self.options))

    def getConfValue(self, stanza, key, defaultValue=None):
        return self.config.get(stanza, {}).get(key, defaultValue)

    def get_java_executable(self):
        return os.path.join(self.java_home, 'bin', "java.exe" if os.name == 'nt' else 'java')

    def get_version(self, overrideOpts=None):
        executable = self.get_java_executable()
        if os.path.exists(executable):
            opts = self.options
            if overrideOpts is not None:
                opts = overrideOpts
            output, err = Popen([executable] + opts + ['-version'], stdout=PIPE, stderr=STDOUT).communicate()
            if output:
                m = re.search("java version \"?([^\s\"]+)\"?", output, flags=re.MULTILINE)
                if m:
                    return JavaVersion(m.group(1))
                raise JavaVersionException(
                    "Unable to determine Java version: %s" % " ".join(output.strip().splitlines()))
        else:
            raise JavaVersionException("Java Home %s is not a Java installation directory!" % self.java_home)
        raise JavaVersionException("Unable to determine Java version!")

    def is_compatible(self, min_major, min_minor):
        v = self.get_version()
        return v and v.getMajor() >= min_major and v.getMinor() >= min_minor

    def get_classpath_separator(self):
        return ';' if os.name == 'nt' else ':'

    def gen_classpath(self, lib_path):
        return self.get_classpath_separator().join(self.get_jar_files(lib_path))

    def get_jar_files(self, lib_path):
        if lib_path:
            jars = []
            for file in os.listdir(lib_path):
                if file.endswith(".jar"):
                    jars.append(os.path.join(lib_path, file))
            return jars
        else:
            return ['.']

    def normalize_subprocess_options(self, **options):
        if 'redirect' in options and options['redirect']:
            if not 'stdin' in options: options['stdin'] = PIPE
            if not 'stdout' in options: options['stdout'] = PIPE
            if not 'stderr' in options: options['stderr'] = PIPE
        else:
            options['stderr'] = PIPE # redirect stderr by default
        if 'redirect' in options: del options['redirect']
        return options

    def execute(self, main_class, args, **options):
        cmd = [self.get_java_executable(), '-cp', self.gen_classpath(self.lib_path)]
        if not args: args = []
        logger.debug("Executing (native) CMD %s" % " ".join(cmd + self.options + [main_class] + args))
        options = self.normalize_subprocess_options(**options)
        return JavaProcess(Popen(cmd + self.options + [main_class] + args, **options))


class JavaProcess:
    def __init__(self, process):
        self.process = process
        self.out = None
        self.err = None

    def send(self, input):
        self.output, self.errout = self.process.communicate(input=input)

    def pipeInput(self, stream):
        for line in stream:
            self.process.stdin.write(line)

    def get_output(self):
        if self.out is not None:
            return self.out #or self.process.stdout.read()
        elif not self.process.stdout.closed:
            return self.process.stdout.read()

    def get_returncode(self):
        return self.process.returncode

    def waitFor(self, checkReturnCode=False):
        self.out, err = self.process.communicate()
        if checkReturnCode:
            if not self.get_returncode() is 0:
                if err:
                    msg = re.sub(r'[\r\n]+', ' ', err)
                else:
                    msg = "Unknown"
                logger.error("Java process returned error code %s! Error: %s", self.get_returncode(), msg)
                logger.error("Command output: %s", self.out)
                raise JavaExecutionException(
                    "Java process returned error code %s! Error: %s" % (self.get_returncode(), msg))
        return self.get_returncode()

    def terminate(self):
        self.process.terminate()


def get_java_version(java_home, overrideOpts=None):
    if overrideOpts is not None:
        overrideOpts = shlex.split(overrideOpts)
    return JavaEnv(java_home=java_home).get_version(overrideOpts=overrideOpts)


def execute(cls, args, **java_options):
    """Executes the given java class with the given arguments and returns the output"""
    env = JavaEnv(**java_options)
    p = env.execute(cls, args, stdout=PIPE)
    return p.get_output()


def autodetect_java_home():
    if os.name == 'posix':
        cur_os = os.uname()[0]
        if cur_os == 'Darwin':
            return autodetect_java_home_osx()
        else:
            return autodetect_java_home_posix()
    elif os.name == 'nt':
        return autodetect_java_home_win()
    else:
        logger.warn("Unable to autodetect JAVA_HOME on platform %s", os.name)
        return ""


def autodetect_java_home_osx():
    path = "/System/Library/Frameworks/JavaVM.framework/Home"
    v = get_java_version(path)
    if v: return path


def autodetect_java_home_posix():
    if "JAVA_HOME" in os.environ:
        path = os.environ['JAVA_HOME']
        v = get_java_version(path)
        if v: return path
    return test_java_in_path()


def autodetect_java_home_win():
    try:
        import _winreg as reg

        root = r'SOFTWARE\JavaSoft\Java Runtime Environment'
        reg_key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, root, 0, reg.KEY_ALL_ACCESS)
        versions = []
        for i in range(255):
            try:
                versions.append(reg.EnumKey(reg_key, i))
            except:
                break
        versions.sort(reverse=True)

        for version in versions:
            key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, "\\".join([root, version]), 0, reg.KEY_ALL_ACCESS)
            path = reg.QueryValueEx(key, "JavaHome")[0]
            if path and os.path.exists(path) and get_java_version(path):
                return path
    except:
        pass


def test_java_in_path():
    try:
        p = Popen(['which', 'java'], stdout=PIPE)
        out = p.communicate()[0]
        if out:
            path = os.path.normpath(os.path.join(os.path.realpath(out.strip()), '..', '..'))
            logger.debug("'which java' returned %s", path)
            v = get_java_version(path)
            if v: return path
    except:
        pass