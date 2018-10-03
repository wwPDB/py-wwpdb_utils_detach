#!/opt/wwpdb/bin/python
#
# File:  DetachedProcessBaseWithLoggingTests.py
# Date:  10-Feb-2015
#
#  Provides example of invoking a detached process which launches a variety of subprocesses.
#
#  Uses dependent utility classes and methods - SubProcessUtil and testTask.py
##

import sys
import os
import time
import logging
from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase
from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil


class TestDetachedProcess(DetachedProcessBase):
    """  This class implements the run() method of the DetachedProcessBase() utility class.

         Illustrates the use of python logging and various I/O channels in detached process.
    """
    def run(self):
        #
        logPath = "mylog_%d.log" % 0
        spu = SubProcessUtil(verbose=True, log=sys.stdout)
        pid = spu.runPythonDetached(pythonFilePath="testTask.py", arguments=" --logfile " + logPath, logFilePath=logPath)
        logger.info("TestDetachedProcess.run() started subprocess %d parent %d group %d\n" % (pid, os.getppid(), os.getpgid(pid)))

        ofh = open("testOutput.log", 'w', 1)
        ic = 0
        while True:
            ic += 1
            sys.stdout.write("+TestDetachedProcess.run() -----------------------------------  stdout: Counter is %d\n" % ic)
            sys.stderr.write("+TestDetachedProcess.run() -----------------------------------  stderr: Counter is %d\n" % ic)
            ofh.write("+TestDetachedProcess.run()           -----------------------------------  ofh: Counter is %d\n" % ic)
            #
            logger.info("+TestDetachedProcess.run() informational message. %d" % ic)
            logger.warning("+TestDetachedProcess.run() warning message %d" % ic)
            logger.debug("_TestDetachedProcess.run() debug message %d" % ic)
            logger.error("+TestDetachedProcess.run() error message %d" % ic)
            time.sleep(1)
            logPath = "mylog_%d.log" % ic
            spu = SubProcessUtil(verbose=True, log=sys.stdout)
            pid = spu.runPythonDetached(pythonFilePath="testTask.py", arguments=" --logfile " + logPath, logFilePath=logPath)
            logger.info("TestDetachedProcess.run() started subprocess %d parent %d group %d\n" % (pid, os.getppid(), os.getpgid(pid)))

        ofh.close()

if __name__ == "__main__":
    wD = os.path.abspath("./")
    #
    logger = logging.getLogger("DetachedProcessLog")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler = logging.FileHandler(os.path.join(wD, "detached-process.log"))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #
    myDP = TestDetachedProcess(pidFile='detached-process-example.pid', stdout="testStdOut.log", stderr="testStdErr.log", wrkDir=wD)
    #    myDP=TestDetachedProcess(pidFile='daemon-example.pid', stdout=handler, stderr=handler, wrkDir=wD)

    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            logger.info("TestDetachedProcessWithLogging STARTING\n")
            myDP.start()
        elif 'stop' == sys.argv[1]:
            myDPSS = TestDetachedProcess(pidFile='detached-process-example.pid', stdout=sys.stdout, stderr=sys.stderr, wrkDir=wD)
            logger.info("TestDetachedProcessWithLogging STOPPING\n")
            myDPSS.stop()
        elif 'restart' == sys.argv[1]:
            logger.info("TestDetachedProcessWithLogging RESTARTING\n")
            myDP.restart()
        elif 'status' == sys.argv[1]:
            logger.info("TestDetachedProcessWithLogging status query:\n%s\n" % myDP.status())
            sys.stderr.write(myDP.status())
        else:
            sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
            sys.exit(2)
        sys.exit(0)
    else:
        sys.stderr.write("Usage: %s start|stop|restart|status\n" % sys.argv[0])
        sys.exit(2)
