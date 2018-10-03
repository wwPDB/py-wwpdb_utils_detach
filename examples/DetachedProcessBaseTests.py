#!/opt/wwpdb/bin/python
#
# File:  DetachedProcessBaseTests.py
# Date:  10-Feb-2015
#
#  Provides example of invoking a detached process which launches a variety of subprocesses.
#
#  Uses dependent utility classes and methods - SubProcessUtil and testTask.py
##

import sys
import os
import time
from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase
from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil

#


class TestDetachedProcess(DetachedProcessBase):

    def run(self):
        ofh = open("TestDetachedProcessOutput.log", 'w', 1)
        ic = 0
        while True:
            ic += 1
            sys.stdout.write("+TestDetachedProcess.run() -----------------------------------  stdout: Counter is %d\n" % ic)
            sys.stderr.write("+TestDetachedProcess.run() -----------------------------------  stderr: Counter is %d\n" % ic)
            ofh.write("+TestDetachedProcess.run()        -----------------------------------  ofh:    Counter is %d\n" % ic)
            time.sleep(1)
            logPath = "mytasklog-%d.log" % ic
            spu = SubProcessUtil(verbose=True, log=sys.stdout)
            pid = spu.runPythonDetached(pythonFilePath="testTask.py", arguments=" --logfile " + logPath, logFilePath=logPath)
        ofh.close()

if __name__ == "__main__":
    wD = os.path.abspath("./")
    #
    myDP = TestDetachedProcess(pidFile='detached-process-example.pid', stdout="testStdOut.log", stderr="testStdErr.log", wrkDir=wD)

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            myDP.start()
        elif 'stop' == sys.argv[1]:
            myDP.stop()
        elif 'restart' == sys.argv[1]:
            myDP.restart()
        elif 'status' == sys.argv[1]:
            sys.stderr.write(myDP.status())
        else:
            sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
            sys.exit(2)
        sys.exit(0)
    else:
        sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
        sys.exit(2)
