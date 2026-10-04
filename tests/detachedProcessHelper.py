##
# File:  detachedProcessHelper.py
# Date:  04-Oct-2026
#
# Helper script launched by DetachedProcessBaseTests to exercise a real detached process.
#
#  Usage: detachedProcessHelper.py start|stop|status <pidFile> <markerFile> <wrkDir>
##
"""Detached process used by DetachedProcessBaseTests"""

import os
import subprocess
import sys
import time

from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase


class HelperProcess(DetachedProcessBase):
    def __init__(self, pidFile: str, markerFile: str, wrkDir: str) -> None:
        super().__init__(
            pidFile=pidFile,
            stdout=os.path.join(wrkDir, "helper-stdout.log"),
            stderr=os.path.join(wrkDir, "helper-stderr.log"),
            wrkDir=wrkDir,
        )
        self.__markerFile = markerFile

    def run(self) -> None:
        # Child process so that status() and stop() have descendants to handle
        child = subprocess.Popen(["sleep", "300"])  # noqa: S607
        sys.stdout.write("helper stdout\n")
        sys.stdout.flush()
        sys.stderr.write("helper stderr\n")
        sys.stderr.flush()
        with open(self.__markerFile, "w") as fout:
            fout.write("%d %d %s\n" % (os.getpid(), child.pid, os.getcwd()))
        while True:
            time.sleep(0.5)


def main() -> None:
    action, pidFile, markerFile, wrkDir = sys.argv[1:5]
    hp = HelperProcess(pidFile=pidFile, markerFile=markerFile, wrkDir=wrkDir)
    if action == "start":
        hp.start()
    elif action == "stop":
        hp.stop()
    elif action == "status":
        sys.stdout.write(hp.status())
    sys.exit(0)


if __name__ == "__main__":
    main()
