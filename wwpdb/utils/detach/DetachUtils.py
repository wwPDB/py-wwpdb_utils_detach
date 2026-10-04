##
# File:    DetachUtils.py
# Date:    06-Mar-2013
#
# Updates:
#   07-Mar-2013  jdw Define method setLogHandle() to implement log redirection.  This method must
#                    must exist on the input object.
##
"""
Manage detached processes

"""

__docformat__ = "restructuredtext en"
__author__ = "John Westbrook"
__email__ = "jwest@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.07"

import os
import sys
import time
import traceback
from typing import Any, Callable, Dict, Optional, TextIO


class DetachUtils(Dict[str, Any]):  # noqa: FURB189
    """Derived dictionary class supporting automatic initialization.

    This will support pickle serialization/deserialization.
    """

    __logFunc: Callable[..., Any]
    __workerFunc: Callable[[], Any]
    __cLog: TextIO

    def __init__(  # pylint: disable=super-init-not-called
        self,
        reqObj: Any = None,
        verbose: bool = True,  # noqa: FBT001
        log: TextIO = sys.stderr,
    ) -> None:
        self.__verbose = verbose
        self.__lfh = log
        self.__reqObj = reqObj
        self.__sessionObj = self.__reqObj.getSessionObj()
        self.__sessionPath = self.__sessionObj.getPath()

    def set(self, workerObj: Any = None, workerMethod: Optional[str] = None) -> bool:
        try:
            self.__logFunc = workerObj.setLogHandle  # pylint: disable=attribute-defined-outside-init
            self.__workerFunc = getattr(  # pylint: disable=attribute-defined-outside-init
                workerObj,
                workerMethod,  # type: ignore[arg-type]
            )
            return True
        except AttributeError:
            self.__lfh.write("+DetachUtils.set() object/attribute error\n")
            return False

    def runDetach(self) -> bool:
        """
        Run the worker function as a detached process --
        """
        siteId = self.__reqObj.getValue("WWPDB_SITE_ID")
        if self.__verbose:
            self.__lfh.write("+DetachUtils.__runDetach() - STARTING\n")

        sph = self.__setSemaphore()
        child_pid = os.fork()
        if child_pid == 0:
            os.setsid()
            sub_pid = os.fork()
            if sub_pid:
                # Parent of second fork
                os._exit(0)  # pylint: disable=protected-access

            sys.stdout = RedirectDevice()
            sys.stderr = RedirectDevice()
            os.setpgrp()
            os.umask(0)
            os.environ["WWPDB_SITE_ID"] = siteId
            #
            # Redirect the logfile for the child process -
            #
            self.__openSemaphoreLog(sph)
            sys.stdout = self.__cLog
            sys.stderr = self.__cLog
            try:
                self.__logFunc(log=self.__cLog)

                if self.__verbose:
                    self.__cLog.write("+DetachUtils.__runDetach() Child Process: PID# %s\n" % os.getpid())
                    self.__cLog.write("+DetachUtils.__runDetach() Site id       %s\n" % siteId)
                ok = self.__workerFunc()

                if ok:
                    self.__postSemaphore(sph, "OK")
                else:
                    self.__postSemaphore(sph, "FAIL")
                self.__cLog.flush()
            except Exception as e:  # noqa: F841,BLE001 pylint: disable=unused-variable
                traceback.print_exc(file=self.__cLog)
                self.__cLog.write("+DetachUtils.__runDetach() Failing for child Process: PID# %s\n" % os.getpid())
                self.__postSemaphore(sph, "FAIL")
                self.__cLog.flush()
            os._exit(0)  # pylint: disable=protected-access

        else:
            # Parent returns status information only -
            #
            if self.__verbose:
                self.__lfh.write("+DetachUtils.__runDetach() PARENT COMPLETED parent process: pid# %s\n" % os.getpid())
            os.waitpid(child_pid, 0)
            return True

    def semaphoreExists(self, semaphore: str = "TMP_") -> bool:
        fPathAbs = os.path.join(self.__sessionPath, semaphore)
        if os.access(fPathAbs, os.F_OK):  # noqa: SIM103
            return True
        return False

    def getSemaphore(self, semaphore: str = "TMP_") -> str:
        fPathAbs = os.path.join(self.__sessionPath, semaphore)
        try:
            fp = open(fPathAbs)
            lines = fp.readlines()
            fp.close()
            sval = lines[0][:-1]
        except Exception as e:  # noqa: F841,BLE001 pylint: disable=unused-variable
            sval = "FAIL"

        if self.__verbose:
            self.__lfh.write(
                "+DetachUtils.__getSemaphore() - checked %s in path %s returning %s \n" % (semaphore, fPathAbs, sval)
            )

        return sval

    def __setSemaphore(self) -> str:
        sVal = str(time.strftime("TMP_%Y%m%d%H%M%S", time.localtime()))
        self.__reqObj.setValue("semaphore", sVal)
        return sVal

    def __openSemaphoreLog(self, semaphore: str = "TMP_") -> None:
        fPathAbs = os.path.join(self.__sessionPath, semaphore + ".log")
        self.__cLog = open(fPathAbs, "w")  # pylint: disable=attribute-defined-outside-init

    # This should be invoked in __del__ likely
    # def __closeSemaphoreLog(self, semaphore="TMP_"):  # pylint: disable=unused-argument
    #     self.__cLog.flush()
    #     self.__cLog.close()

    def __postSemaphore(self, semaphore: str = "TMP_", value: str = "OK") -> str:
        fPathAbs = os.path.join(self.__sessionPath, semaphore)
        fp = open(fPathAbs, "w")
        fp.write("%s\n" % value)
        fp.close()
        return semaphore


class RedirectDevice:
    def write(self, s: str) -> None:
        pass
