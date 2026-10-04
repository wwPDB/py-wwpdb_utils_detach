##
# File:  DetachedProcessBaseTests.py
# Date:  04-Oct-2026
#
# Updates:
##
"""Test cases for DetachedProcessBase"""

from __future__ import annotations

import contextlib
import errno
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from signal import SIGKILL, SIGTERM
from typing import Callable
from unittest import mock

import psutil

from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase

HERE = os.path.abspath(os.path.dirname(__file__))
HELPER = os.path.join(HERE, "detachedProcessHelper.py")
MODULE = "wwpdb.utils.detach.DetachedProcessBase"


class RecordingProcess(DetachedProcessBase):
    """Subclass that records calls to the overridable entry points"""

    def __init__(self, pidFile: str, wrkDir: str = "/", uid: int = 0, gid: int = 0) -> None:
        super().__init__(
            pidFile=pidFile,
            stdout=os.path.join(wrkDir, "stdout.log"),
            stderr=os.path.join(wrkDir, "stderr.log"),
            wrkDir=wrkDir,
            uid=uid,
            gid=gid,
        )
        self.calls: list[str] = []

    def run(self) -> None:
        self.calls.append("run")

    def suspend(self) -> bool:
        self.calls.append("suspend")
        return True


def waitFor(predicate: Callable[[], bool], timeout: float = 20.0) -> bool:
    tEnd = time.time() + timeout
    while time.time() < tEnd:
        if predicate():
            return True
        time.sleep(0.1)
    return False


class DetachedProcessBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.__wrkDir = os.path.realpath(tempfile.mkdtemp(prefix="detached-test-"))
        self.__pidFile = os.path.join(self.__wrkDir, "test.pid")

    def tearDown(self) -> None:
        shutil.rmtree(self.__wrkDir, ignore_errors=True)

    def __writePid(self, pid: int) -> None:
        with open(self.__pidFile, "w") as fout:
            fout.write("%d\n" % pid)

    def testDefaults(self) -> None:
        dp = DetachedProcessBase(pidFile=self.__pidFile)
        dp.run()
        self.assertTrue(dp.suspend())

    def testStatusNoPidFile(self) -> None:
        dp = DetachedProcessBase(pidFile=self.__pidFile)
        self.assertEqual(dp.status(), "+DetachedProcessBase.status(): No active process is running.\n")

    def testStatusBadPidFile(self) -> None:
        with open(self.__pidFile, "w") as fout:
            fout.write("not-a-pid\n")
        dp = DetachedProcessBase(pidFile=self.__pidFile)
        self.assertIn("No active process is running", dp.status())

    def testStatusRunning(self) -> None:
        """Point the pid file at this process and report its child"""
        self.__writePid(os.getpid())
        child = subprocess.Popen(["sleep", "30"])  # noqa: S607
        try:
            dp = DetachedProcessBase(pidFile=self.__pidFile)
            msg = dp.status()
        finally:
            child.terminate()
            child.wait()
        self.assertIn("active process id is %d (process group %d)" % (os.getpid(), os.getpgid(0)), msg)
        self.assertIn("child process id: %d  parent %d name sleep" % (child.pid, os.getpid()), msg)

    def testStartWhenRunning(self) -> None:
        self.__writePid(os.getpid())
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir)
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err, mock.patch(
            "%s.os.fork" % MODULE
        ) as fork, self.assertRaises(SystemExit) as cm:
            dp.start()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("exists and process is running", err.getvalue())
        fork.assert_not_called()
        self.assertEqual(dp.calls, [])

    def testStartForkFailure(self) -> None:
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir)
        forkErr = OSError(errno.EAGAIN, "Resource temporarily unavailable")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err, mock.patch(
            "%s.os.fork" % MODULE, side_effect=forkErr
        ), self.assertRaises(SystemExit) as cm:
            dp.start()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Failing with %d (Resource temporarily unavailable)" % errno.EAGAIN, err.getvalue())
        self.assertEqual(dp.calls, [])

    def testStartSecondForkFailure(self) -> None:
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir, uid=os.getuid(), gid=os.getgid())
        forkErr = OSError(errno.EAGAIN, "Resource temporarily unavailable")
        cwd = os.getcwd()
        oldMask = os.umask(0o022)
        try:
            osPatch = mock.patch.multiple(
                "%s.os" % MODULE, fork=mock.DEFAULT, setsid=mock.DEFAULT, setgid=mock.DEFAULT, setuid=mock.DEFAULT
            )
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err, osPatch as osMocks:
                osMocks["fork"].side_effect = [0, forkErr]
                with self.assertRaises(SystemExit) as cm:
                    dp.start()
        finally:
            os.chdir(cwd)
            os.umask(oldMask)
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("Failing with", err.getvalue())
        self.assertEqual(dp.calls, [])

    def testStartParentExits(self) -> None:
        """The original parent exits cleanly after the first fork"""
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir)
        with mock.patch("%s.os.fork" % MODULE, return_value=12345), self.assertRaises(SystemExit) as cm:
            dp.start()
        self.assertEqual(cm.exception.code, 0)
        self.assertEqual(dp.calls, [])

    def __startInProcess(
        self, umask: int, setuidErr: bool = False
    ) -> tuple[RecordingProcess, mock.MagicMock, mock.MagicMock, int]:
        """Run start() in this process with the forking and descriptor redirection mocked out.

        Returns the process object, the stderr mock, the atexit.register mock, and the resulting umask.
        """
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir, uid=1111, gid=2222)
        cwd = os.getcwd()
        oldMask = os.umask(umask)
        setuid = mock.MagicMock(side_effect=PermissionError("not permitted") if setuidErr else None)
        try:
            osPatch = mock.patch.multiple(
                "%s.os" % MODULE,
                fork=mock.DEFAULT,
                setsid=mock.DEFAULT,
                setgid=mock.DEFAULT,
                setuid=setuid,
                dup2=mock.DEFAULT,
            )
            registerPatch = mock.patch("%s.atexit.register" % MODULE)
            with osPatch as osMocks, registerPatch as register, mock.patch("sys.stderr") as err:
                osMocks["fork"].return_value = 0
                dp.start()
                newCwd = os.getcwd()
        finally:
            os.chdir(cwd)
            newMask = os.umask(oldMask)

        self.assertEqual(newCwd, self.__wrkDir)
        osMocks["setsid"].assert_called_once_with()
        osMocks["setgid"].assert_called_once_with(2222)
        if not setuidErr:
            setuid.assert_called_once_with(1111)
        self.assertEqual(osMocks["dup2"].call_count, 3)
        self.assertEqual(dp.calls, ["run"])
        with open(self.__pidFile) as fin:
            self.assertEqual(fin.read(), "%d\n" % os.getpid())
        self.assertTrue(os.path.exists(os.path.join(self.__wrkDir, "stdout.log")))
        self.assertTrue(os.path.exists(os.path.join(self.__wrkDir, "stderr.log")))
        return dp, err, register, newMask

    def testStartInProcess(self) -> None:
        _dp, _err, register, newMask = self.__startInProcess(umask=0o077)
        self.assertEqual(newMask, 0o077)
        # The registered exit handler removes the pid file
        register.assert_called_once()
        cleanup = register.call_args[0][0]
        cleanup()
        self.assertFalse(os.path.exists(self.__pidFile))
        cleanup()  # Harmless when already removed

    def testStartFixesUmask(self) -> None:
        _dp, _err, _register, newMask = self.__startInProcess(umask=0)
        self.assertEqual(newMask, 0o022)

    def testStartOwnerGroupFailure(self) -> None:
        _dp, err, _register, _newMask = self.__startInProcess(umask=0o022, setuidErr=True)
        written = "".join(str(c[0][0]) for c in err.write.call_args_list)
        self.assertIn("+DetachedProcessBase.__setOwnerGroup failing (not permitted)", written)

    def testStopNoPidFile(self) -> None:
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            dp.stop()
        self.assertEqual(dp.calls, ["suspend"])
        self.assertIn("Process file %s does not exist" % self.__pidFile, err.getvalue())

    def testStopProcessGone(self) -> None:
        """Process exits while being killed - pid file is cleaned up"""
        self.__writePid(424242)
        dp = RecordingProcess(pidFile=self.__pidFile)
        proc = mock.MagicMock()
        proc.children.return_value = [mock.MagicMock(pid=424243)]
        osPatch = mock.patch.multiple("%s.os" % MODULE, kill=mock.DEFAULT, getpgid=mock.DEFAULT, killpg=mock.DEFAULT)
        with mock.patch("%s.psutil.Process" % MODULE, return_value=proc), mock.patch(
            "%s.time.sleep" % MODULE
        ), osPatch as osMocks:
            osMocks["getpgid"].return_value = 424242
            osMocks["killpg"].side_effect = [None, ProcessLookupError(errno.ESRCH, "No such process")]
            dp.stop()
        kill = osMocks["kill"]
        killpg = osMocks["killpg"]
        self.assertEqual(dp.calls, ["suspend"])
        proc.children.assert_called_once_with(recursive=True)
        self.assertEqual(
            kill.call_args_list,
            [mock.call(424243, SIGTERM), mock.call(424242, SIGKILL)],
        )
        self.assertEqual(killpg.call_count, 2)
        self.assertFalse(os.path.exists(self.__pidFile))

    def testStopStalePidFile(self) -> None:
        """Pid file refers to a process that has exited - pid file is cleaned up"""
        child = subprocess.Popen(["true"])  # noqa: S607
        child.wait()
        self.__writePid(child.pid)
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            dp.stop()
        self.assertEqual(dp.calls, ["suspend"])
        self.assertEqual(err.getvalue(), "")
        self.assertFalse(os.path.exists(self.__pidFile))

    def testStopZombieProcess(self) -> None:
        self.__writePid(424242)
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("%s.psutil.Process" % MODULE, side_effect=psutil.ZombieProcess(424242)):
            dp.stop()
        self.assertFalse(os.path.exists(self.__pidFile))

    def testStopBadPidFile(self) -> None:
        """Pid file without a valid process id is reported, not raised"""
        with open(self.__pidFile, "w") as fout:
            fout.write("not-a-pid\n")
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            dp.stop()
        self.assertEqual(dp.calls, ["suspend"])
        self.assertIn("Process file %s does not exist or has no valid process id" % self.__pidFile, err.getvalue())

    def testStartBadPidFile(self) -> None:
        """A pid file without a valid process id does not block start()"""
        with open(self.__pidFile, "w") as fout:
            fout.write("not-a-pid\n")
        dp = RecordingProcess(pidFile=self.__pidFile, wrkDir=self.__wrkDir)
        with mock.patch("%s.os.fork" % MODULE, return_value=12345) as fork, self.assertRaises(SystemExit) as cm:
            dp.start()
        self.assertEqual(cm.exception.code, 0)
        fork.assert_called_once_with()

    def testStopLegacyNoProcessMessage(self) -> None:
        self.__writePid(424242)
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("%s.psutil.Process" % MODULE, side_effect=RuntimeError("no process found with pid 424242")):
            dp.stop()
        self.assertFalse(os.path.exists(self.__pidFile))

    def testStopUnexpectedError(self) -> None:
        self.__writePid(424242)
        dp = RecordingProcess(pidFile=self.__pidFile)
        with mock.patch("%s.psutil.Process" % MODULE, side_effect=psutil.AccessDenied(424242)), mock.patch(
            "sys.stderr", new_callable=io.StringIO
        ) as err, self.assertRaises(SystemExit) as cm:
            dp.stop()
        self.assertEqual(cm.exception.code, 1)
        self.assertNotEqual(err.getvalue(), "")
        self.assertTrue(os.path.exists(self.__pidFile))

    def testRestart(self) -> None:
        dp = RecordingProcess(pidFile=self.__pidFile)
        order = mock.MagicMock()
        with mock.patch.object(dp, "stop", order.stop), mock.patch.object(dp, "start", order.start):
            dp.restart()
        self.assertEqual(order.mock_calls, [mock.call.stop(), mock.call.start()])


class DetachedProcessLifecycleTests(unittest.TestCase):
    """Start a real detached process, query it and stop it"""

    def setUp(self) -> None:
        self.__wrkDir = os.path.realpath(tempfile.mkdtemp(prefix="detached-life-"))
        self.__pidFile = os.path.join(self.__wrkDir, "helper.pid")
        self.__marker = os.path.join(self.__wrkDir, "marker")

    def tearDown(self) -> None:
        # Safety net in case the test failed before stop()
        if os.path.exists(self.__marker):
            with open(self.__marker) as fin:
                for tok in fin.read().split()[:2]:
                    with contextlib.suppress(OSError, ValueError):
                        os.kill(int(tok), SIGKILL)

        shutil.rmtree(self.__wrkDir, ignore_errors=True)

    def __helper(self, action: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, HELPER, action, self.__pidFile, self.__marker, self.__wrkDir],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def testLifecycle(self) -> None:
        res = self.__helper("start")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(waitFor(lambda: os.path.exists(self.__marker) and os.path.getsize(self.__marker) > 0))
        self.assertTrue(waitFor(lambda: os.path.exists(self.__pidFile)))

        with open(self.__marker) as fin:
            pidS, childS, cwd = fin.read().split()
        pid, childPid = int(pidS), int(childS)
        with open(self.__pidFile) as fin:
            self.assertEqual(int(fin.read()), pid)
        self.assertEqual(cwd, self.__wrkDir)
        # Detached process runs in a new session (created before the second fork) and process group
        self.assertNotEqual(os.getsid(pid), os.getsid(0))
        self.assertNotEqual(os.getsid(pid), pid)
        self.assertEqual(os.getpgid(pid), os.getsid(pid))

        # Output was redirected
        self.assertTrue(
            waitFor(lambda: "helper stdout" in open(os.path.join(self.__wrkDir, "helper-stdout.log")).read())
        )
        self.assertTrue(
            waitFor(lambda: "helper stderr" in open(os.path.join(self.__wrkDir, "helper-stderr.log")).read())
        )

        dp = DetachedProcessBase(pidFile=self.__pidFile)
        status = dp.status()
        self.assertIn("active process id is %d" % pid, status)
        self.assertIn("child process id: %d" % childPid, status)

        # Second start refuses to run
        res = self.__helper("start")
        self.assertEqual(res.returncode, 1)
        self.assertIn("exists and process is running", res.stderr)

        dp.stop()
        self.assertFalse(os.path.exists(self.__pidFile))
        self.assertTrue(
            waitFor(lambda: not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE)
        )
        self.assertTrue(
            waitFor(
                lambda: not psutil.pid_exists(childPid) or psutil.Process(childPid).status() == psutil.STATUS_ZOMBIE
            )
        )
        self.assertIn("No active process is running", dp.status())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
