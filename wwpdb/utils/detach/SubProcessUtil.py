##
# File: SubProcessUtil.py
# Date: 10-Feb-2015  J. Westbrook
# #
import datetime
import os
import signal
import stat
import subprocess
import sys
import time


class SubProcessUtil:
    """  Skeleton methods supporting running shell and python scripts as subprocesses.

         These methods are provided primarily to support testing other classes.
    """

    def __init__(self, verbose=True, log=sys.stdout):
        self.__lfh = log
        self.__verbose = verbose
        self.__wrkPath = '.'

    def runPythonDetached(self, pythonFilePath, arguments="", logFilePath="testlog.log"):
        return self.__runPyDetached(pythonFilePath=pythonFilePath, arguments=arguments, logFilePath=logFilePath)

    def __runPyDetached(self, pythonFilePath, arguments="", logFilePath="testlog.log"):
        """
        """
        commandString = "%s %s %s >> %s 2>&1" % (sys.executable, pythonFilePath, arguments, logFilePath)
        return self.__runCommandDetached(commandString)

    def __runCommandDetached(self, commandString):
        self.__lfh.write("SubProcessUtil.__runCommandDetached() running command string:\n %r\n" % commandString)
        pid = subprocess.Popen(commandString, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, close_fds=True, preexec_fn=os.setsid).pid
        # pid = subprocess.Popen(commandString, stdout=None, stderr=None, shell=True, preexec_fn=os.setsid).pid
        return pid

    def __runCommandFileDetached(self, commandFilePath):
        self.__lfh.write("SubProcessUtil.__runProcessDetached() running command file %r\n" % commandFilePath)
        process = subprocess.Popen(commandFilePath, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True, preexec_fn=os.setsid)
        return process.pid

    def __wrapInShell(self, commandFilePath, commandString):
        """ Embed the input command string within a Bourne shell packaged in the
            input command file path.
        """
        try:
            ofh = open(commandFilePath, 'w')
            ofh.write("#!/bin/sh\n")
            ofh.write(commandString)
            ofh.write("\n#\n")
            ofh.close()
            st = os.stat(commandFilePath)
            os.chmod(commandFilePath, st.st_mode | stat.S_IEXEC)
            return True
        except Exception as e:
            return False

    def __runPyDetachedInShell(self, pythonFilePath, arguments="", stdoutFilePath=os.devnull, stderrFilePath=os.devnull):
        """
        """
        commandString = "python %s %s 1> %s 2> %s &" % (pythonFilePath, arguments, stdoutFilePath, stderrFilePath)
        ok = self.__wrapInShell("./test.sh", commandString)
        if ok:
            return self.__runCommandFileDetached("./test.sh")
        else:
            return -1

    def __runTimeout(self, commandString, timeout, logPath=None):
        """ Execute the input command string (sh semantics) as a subprocess with a timeout.

        """
        start = datetime.datetime.now()
        cmdfile = os.path.join(self.__wrkPath, 'timeoutscript.sh')
        self.__wrapInShell(commandString, cmdfile)
        self.__lfh.write("+__runTimeout() running command %r\n" % cmdfile)
        process = subprocess.Popen(cmdfile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True, preexec_fn=os.setsid)
        while process.poll() is None:
            time.sleep(0.1)
            now = datetime.datetime.now()
            if (now - start).seconds > timeout:
                # os.kill(-process.pid, signal.SIGKILL)
                os.killpg(process.pid, signal.SIGKILL)
                os.waitpid(-1, os.WNOHANG)
                self.__lfh.write("+ERROR __runTimeout() - Execution terminated by timeout %d (seconds)\n" % timeout)
                if logPath is not None:
                    ofh = open(logPath, 'a')
                    ofh.write("+ERROR __runTimeout() Execution terminated by timeout %d (seconds)\n" % timeout)
                    ofh.close()
                return None
        self.__lfh.write("+__runTimeout() completed with return code %r\n" % process.stdout.read())
        return 0


if __name__ == "__main__":
    spu = SubProcessUtil(verbose=True, log=sys.stdout)
    pid = spu.runPythonDetached(pythonFilePath="testTask.py", arguments=" --logfile mylog.log", logFilePath="mylog.log")
    sys.stdout.write("PROCESS ID = %d\n" % pid)
    #
    #
