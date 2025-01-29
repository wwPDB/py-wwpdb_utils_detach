#
# File:  DetachedProcessBaseTests.py
# Date:  10-Feb-2015
#
#  Provides example of invoking a detached process which launches a variety of subprocesses.
#
#  Uses dependent utility classes and methods - SubProcessUtil and testTask.py
##

import os
import sys
import time

from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase
from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil


class TestDetachedProcess(DetachedProcessBase):
    @staticmethod
    def run():
        ofh = open("TestDetachedProcessOutput.log", "w", 1)
        ic = 0
        while True:
            ic += 1
            sys.stdout.write(
                "+TestDetachedProcess.run() -----------------------------------  stdout: Counter is %d\n" % ic
            )
            sys.stderr.write(
                "+TestDetachedProcess.run() -----------------------------------  stderr: Counter is %d\n" % ic
            )
            ofh.write(
                "+TestDetachedProcess.run()        -----------------------------------  ofh:    Counter is %d\n" % ic
            )
            time.sleep(1)
            logPath = "mytasklog-%d.log" % ic
            spu = SubProcessUtil(verbose=True, log=sys.stdout)
            _pid = spu.runPythonDetached(
                pythonFilePath="testTask.py",
                arguments=" --logfile " + logPath,
                logFilePath=logPath,
            )
        ofh.close()


if __name__ == "__main__":
    wD = os.path.abspath("./")
    myDP = TestDetachedProcess(
        pidFile="detached-process-example.pid",
        stdout="testStdOut.log",
        stderr="testStdErr.log",
        wrkDir=wD,
    )

    if len(sys.argv) == 2:  # noqa: PLR2004
        if sys.argv[1] == "start":
            myDP.start()
        elif sys.argv[1] == "stop":
            myDP.stop()
        elif sys.argv[1] == "restart":
            myDP.restart()
        elif sys.argv[1] == "status":
            sys.stderr.write(myDP.status())
        else:
            sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
            sys.exit(2)
        sys.exit(0)
    else:
        sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
        sys.exit(2)
