##
# File: testTask.py
# Date: 10-Feb-2015
#
# Example task which exercises various I/O and logging channels.
#
# Part of the testing suite for the detached process utility class.
#
##
import time
import sys
import os
from optparse import OptionParser  # pylint: disable=deprecated-module
import logging


def myTestTask(lfh, maxIterations=10, pauseSeconds=2):
    logger = logging.getLogger(__name__)
    logger.info("+myTestTask STARTING with pid %d ppid %d and pgid %d\n", os.getpid(), os.getppid(), os.getpgid(os.getpid()))

    for i in range(maxIterations):
        time.sleep(pauseSeconds)

        lfh.write("+myTestTask() internal log now on iteration %d\n" % i)
        lfh.flush()

        sys.stdout.write("+myTestTask() sys.stdout now on iteration %d\n" % i)
        sys.stdout.flush()

        sys.stderr.write("+myTestTask() sys.stderr now on iteration %d\n" % i)
        logger.info("++myTestTask now on iteration %d", i)

    return i


def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("--logfile", type="string", dest="logFilePath", help="Log file path - logfile.log")

    (options, _args) = parser.parse_args()

    if options.logFilePath:
        lfh = open(options.logFilePath, "a")
        myTestTask(lfh=lfh)
        lfh.close()
    else:
        myTestTask(lfh=sys.stdout)

    sys.exit(0)


if __name__ == "__main__":
    main()
