##
# File:  SubProcessUtilTests.py
# Date:  04-Oct-2026
#
# Updates:
##
"""Test cases for SubProcessUtil"""

import io
import os
import shutil
import sys
import tempfile
import time
import unittest

from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil

SCRIPT = """
import os
import sys

with open(sys.argv[1], "w") as fout:
    fout.write("args=%s\\n" % " ".join(sys.argv[2:]))
    fout.write("sid=%d\\n" % os.getsid(0))
sys.stdout.write("stdout line\\n")
sys.stderr.write("stderr line\\n")
"""


class SubProcessUtilTests(unittest.TestCase):
    def setUp(self) -> None:
        self.__wrkDir = tempfile.mkdtemp(prefix="subprocess-test-")
        self.__scriptPath = os.path.join(self.__wrkDir, "script.py")
        with open(self.__scriptPath, "w") as fout:
            fout.write(SCRIPT)
        self.__outPath = os.path.join(self.__wrkDir, "out.txt")
        self.__logPath = os.path.join(self.__wrkDir, "run.log")

    def tearDown(self) -> None:
        shutil.rmtree(self.__wrkDir, ignore_errors=True)

    @staticmethod
    def __waitForExit(pid: int, timeout: float = 20.0) -> bool:
        tEnd = time.time() + timeout
        while time.time() < tEnd:
            try:
                rPid, _status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:  # pragma: no cover
                # Already reaped by subprocess's own bookkeeping (Popen.__del__ / subprocess._cleanup)
                return True
            if rPid == pid:
                return True
            time.sleep(0.1)
        return False  # pragma: no cover

    def testRunPythonDetached(self) -> None:
        log = io.StringIO()
        spu = SubProcessUtil(verbose=True, log=log)
        pid = spu.runPythonDetached(
            pythonFilePath=self.__scriptPath,
            arguments="%s alpha beta" % self.__outPath,
            logFilePath=self.__logPath,
        )
        self.assertIsInstance(pid, int)
        self.assertGreater(pid, 0)
        self.assertTrue(self.__waitForExit(pid))

        # Child is started in its own session (led by the returned process)
        with open(self.__outPath) as fin:
            self.assertEqual(fin.read(), "args=alpha beta\nsid=%d\n" % pid)
        with open(self.__logPath) as fin:
            logText = fin.read()
        self.assertIn("stdout line", logText)
        self.assertIn("stderr line", logText)

        msg = log.getvalue()
        self.assertIn("SubProcessUtil.__runCommandDetached() running command string", msg)
        self.assertIn(sys.executable, msg)
        self.assertIn(self.__scriptPath, msg)
        self.assertIn(">> %s 2>&1" % self.__logPath, msg)

    def testLogAppends(self) -> None:
        with open(self.__logPath, "w") as fout:
            fout.write("previous content\n")
        spu = SubProcessUtil(log=io.StringIO())
        pid = spu.runPythonDetached(
            pythonFilePath=self.__scriptPath, arguments=self.__outPath, logFilePath=self.__logPath
        )
        self.assertTrue(self.__waitForExit(pid))
        with open(self.__logPath) as fin:
            logText = fin.read()
        self.assertTrue(logText.startswith("previous content\n"))
        self.assertIn("stdout line", logText)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
