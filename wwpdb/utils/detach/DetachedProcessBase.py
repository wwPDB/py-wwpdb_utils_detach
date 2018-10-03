##
# File: DetachedProcessBase.py
# Date: 10-Feb-2015  J. Westbrook --
#
# Update: 4-Mar-2016 jdw add explicit adjustments to the umask - if it appears that
#                        unset -- (e.g. default assignment 022).
#
##

import atexit
import os
import sys
import time
from signal import SIGKILL
from signal import SIGTERM

import psutil


class DetachedProcessBase(object):

    """
        Base class for managing a detached process.

        Subclass the base class run() method as desired.
    """

    def __init__(self, pidFile='/tmp/DetachedProcessBase.pid', stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, wrkDir='/',
                 gid=None, uid=None):
        self.__stdin = stdin
        self.__stdout = stdout
        self.__stderr = stderr
        self.__pidFile = pidFile
        self.__wrkDir = wrkDir
        if uid is None:
            uid = os.getuid()
        self.__uid = uid
        if gid is None:
            gid = os.getgid()
        self.__gid = gid

    def __detachPrep(self):
        """
        Internal method to prepare the execution environment for the detached process.

        """
        # Fork twice and then redirect the standard file descriptors -
        #
        # First fork -
        try:
            pid = os.fork()
            if pid > 0:
                # clean exit from the first parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("+DetachedProcessBase.__detachPrep(): Failing with %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        #
        os.chdir(self.__wrkDir)
        #
        # Certain privileges will be required to change owner and group -
        self.__setOwnerGroup(self.__uid, self.__gid)
        #
        os.setsid()
        #
        #  Test for a sensible umask -
        #
        utest = os.umask(0o022)
        if utest < 2:
            os.umask(0o022)
        else:
            os.umask(utest)
        #
        #  Second fork -
        try:
            pid = os.fork()
            if pid > 0:
                # clean exit from the second parent
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("+DetachedProcessBase.__detachPrep(): Failing with %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # Redirect the stdin, stdout and stderr descriptors to the alternative files assigned in the
        #  constructor --
        sys.stdout.flush()
        sys.stderr.flush()
        stdInFh = open(self.__stdin, 'r')
        os.dup2(stdInFh.fileno(), sys.stdin.fileno())
        #

        stdOutFh = open(self.__stdout, 'a+', 0)
        stdErrFh = open(self.__stderr, 'a+', 0)
        os.dup2(stdOutFh.fileno(), sys.stdout.fileno())
        os.dup2(stdErrFh.fileno(), sys.stderr.fileno())

        # Register an exit handler to cleanup the process id file -
        atexit.register(self._deletePidFile)

        # Store the process id for the detached process -
        pid = str(os.getpid())
        open(self.__pidFile, 'w+').write("%s\n" % pid)

    def _deletePidFile(self):
        """
        Method to remove the sentinnel file containing the process id.
        """
        if os.path.exists(self.__pidFile):
            os.remove(self.__pidFile)

    def __getPidFromFile(self):
        """
        Internal method to read process id file and return the process id.
        """
        try:
            pf = open(self.__pidFile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
        return pid

    def __isRunning(self):
        """  Internal method to read the current process id and check if the process
             is active.
        """
        try:
            pid = self.__getPidFromFile()
            #  Further check if the process id is active -
            if pid in psutil.get_pid_list():
                return True
            else:
                return False
        except Exception as e:
            try:
                pid = self.__getPidFromFile()
                #  Further check if the process id is active -
                if pid in psutil.pids():
                    return True
                else:
                    return False

            except Exception as e:
                pass
        return False

    def __setOwnerGroup(self, uid, gid):
        """
        Internal method to set the owner UID and GID of this process.  Requires a special privileges
        to change the uid/gid.
        """
        try:
            os.setgid(gid)
            os.setuid(uid)
            return True
        except Exception as e:
            sys.stderr.write("+DetachedProcessBase.__setOwnerGroup failing  %d (%s)\n" % (e.errno, e.strerror))
        return False

    def start(self):
        """
        Start the application as detached process -
        """
        if self.__isRunning():
            sys.stderr.write("+DetachedProcessBase.start(): Process file %s exists and process is running.\n" % self.__pidFile)
            sys.exit(1)

        self.__detachPrep()
        self.run()

    def stop(self):
        """
        Stop the detached process and remove the process id file -

        Kill current process and any descend/child processes.

        """
        # Graceful suspend activity prior to the kill -
        self.suspend()
        #
        pid = self.__getPidFromFile()
        if not pid:
            sys.stderr.write("+DetachedProcessBase.stop(): Process file %s does not exist.\n" % self.__pidFile)
            return

        try:
            p = psutil.Process(pid)
            cPidList = p.children(recursive=True)
            for cPid in cPidList:
                iPid = int(str(cPid.pid))
                os.kill(iPid, SIGTERM)

            while True:
                os.killpg(os.getpgid(pid), SIGKILL)
                os.kill(pid, SIGKILL)
                time.sleep(0.1)
        except Exception as err:
            err = str(err)
            if ((err.find("No such process") != -1) or (err.find("no process found") != -1)):
                self._deletePidFile()
            else:
                sys.stderr.write(str(err))
                sys.exit(1)

    def restart(self):
        """
        Restart the application as a detached process --
        """
        self.stop()
        self.start()

    def status(self):
        """
        Report the current status of the detached process and any process descendents.
        """
        msgList = []
        if self.__isRunning():
            pid = self.__getPidFromFile()
            msgList.append("+DetachedProcessBase.status(): active process id is %d (process group %d)\n" % (pid, os.getpgid(pid)))
            p = psutil.Process(pid)
            cPidList = p.children(recursive=True)
            for cPid in cPidList:
                iPid = int(str(cPid.pid))
                cp = psutil.Process(iPid)
                msgList.append("+DetachedProcessBase.status(): child process id: %d  parent %d name %s (process group %d)\n" %
                               (iPid, cp.ppid(), cp.name(), os.getpgid(pid)))

        else:
            msgList.append("+DetachedProcessBase.status(): No active process is running.\n")

        return ''.join(msgList)

    def run(self):
        """
        This is the entry point for the detached process.  Subclass this method and use the
        start(), stop(), restart() and status() methods to manage the process.
        """

    def suspend(self):
        """
        This is an optional entry point to gracefully suspend the detached process before stopping/killing.
        Subclass this method in the worker class. This method will be called prior to the stop() method.
        """
        return True
