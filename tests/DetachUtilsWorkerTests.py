##
# File:  DetachUtilsWorkerTests.py
# Date:  04-Oct-2026
#
# Updates:
##
"""Test cases for DetachUtils using a stand-in request object (no wwpdb.utils.session dependency)"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import time
import unittest
from typing import IO

from wwpdb.utils.detach.DetachUtils import DetachUtils, RedirectDevice


class FakeSession:
    def __init__(self, path: str) -> None:
        self.__path = path

    def getPath(self) -> str:
        return self.__path


class FakeRequest:
    """Minimal stand-in for wwpdb.utils.session.WebRequest.InputRequest"""

    def __init__(self, sessionPath: str, siteId: str = "TESTSITE") -> None:
        self.__session = FakeSession(sessionPath)
        self.__values: dict[str, str] = {"WWPDB_SITE_ID": siteId}

    def getSessionObj(self) -> FakeSession:
        return self.__session

    def getValue(self, key: str) -> str:
        return self.__values.get(key, "")

    def setValue(self, key: str, value: str) -> None:
        self.__values[key] = value


class Worker:
    """Worker object handed to DetachUtils.set()"""

    def __init__(self, outPath: str) -> None:
        self.__outPath = outPath
        self.__log: IO[str] | None = None

    def setLogHandle(self, log: IO[str]) -> bool:
        self.__log = log
        return True

    def succeed(self) -> bool:
        with open(self.__outPath, "w") as fout:
            fout.write("site=%s\n" % os.environ.get("WWPDB_SITE_ID", ""))
        if self.__log is not None:
            self.__log.write("Worker succeeded\n")
        return True

    @staticmethod
    def fail() -> bool:
        return False

    @staticmethod
    def explode() -> bool:
        raise ValueError("Worker exploded")


class NoLogHandleWorker:
    @staticmethod
    def work() -> bool:
        return True


class DetachUtilsWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.__sessionPath = tempfile.mkdtemp(prefix="detach-test-")
        self.__outPath = os.path.join(self.__sessionPath, "worker-output")
        self.__log = io.StringIO()

    def tearDown(self) -> None:
        shutil.rmtree(self.__sessionPath, ignore_errors=True)

    def __writeSemaphore(self, name: str, value: str) -> None:
        with open(os.path.join(self.__sessionPath, name), "w") as fout:
            fout.write("%s\n" % value)

    @staticmethod
    def __waitForSemaphore(du: DetachUtils, sph: str, timeout: float = 20.0) -> bool:
        tEnd = time.time() + timeout
        while time.time() < tEnd:
            if du.semaphoreExists(sph):
                # Allow the child to finish writing
                time.sleep(0.2)
                return True
            time.sleep(0.1)
        return False

    def __runWorker(self, method: str, siteId: str = "TESTSITE") -> str:
        """Run worker method detached and return the semaphore name"""
        reqObj = FakeRequest(self.__sessionPath, siteId=siteId)
        du = DetachUtils(reqObj, verbose=True, log=self.__log)
        self.assertTrue(du.set(workerObj=Worker(self.__outPath), workerMethod=method))
        self.assertTrue(du.runDetach())
        sph = reqObj.getValue("semaphore")
        self.assertTrue(sph.startswith("TMP_"))
        self.assertTrue(self.__waitForSemaphore(du, sph), "Semaphore %s never posted" % sph)
        return sph

    def __readChildLog(self, sph: str) -> str:
        with open(os.path.join(self.__sessionPath, sph + ".log")) as fin:
            return fin.read()

    def testSetSuccess(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), log=self.__log)
        self.assertTrue(du.set(workerObj=Worker(self.__outPath), workerMethod="succeed"))
        self.assertEqual(self.__log.getvalue(), "")

    def testSetMissingMethod(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), log=self.__log)
        self.assertFalse(du.set(workerObj=Worker(self.__outPath), workerMethod="noSuchMethod"))
        self.assertIn("+DetachUtils.set() object/attribute error", self.__log.getvalue())

    def testSetMissingLogHandle(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), log=self.__log)
        self.assertFalse(du.set(workerObj=NoLogHandleWorker(), workerMethod="work"))
        self.assertIn("+DetachUtils.set() object/attribute error", self.__log.getvalue())

    def testSemaphoreExists(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), log=self.__log)
        self.assertFalse(du.semaphoreExists("TMP_missing"))
        self.__writeSemaphore("TMP_present", "OK")
        self.assertTrue(du.semaphoreExists("TMP_present"))

    def testGetSemaphoreVerbose(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=True, log=self.__log)
        self.__writeSemaphore("TMP_ok", "OK")
        self.__writeSemaphore("TMP_fail", "FAIL")
        self.assertEqual(du.getSemaphore("TMP_ok"), "OK")
        self.assertEqual(du.getSemaphore("TMP_fail"), "FAIL")
        self.assertEqual(du.getSemaphore("TMP_missing"), "FAIL")
        logText = self.__log.getvalue()
        self.assertIn("checked TMP_ok", logText)
        self.assertIn("returning OK", logText)
        self.assertIn("checked TMP_missing", logText)

    def testGetSemaphoreQuiet(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=False, log=self.__log)
        self.__writeSemaphore("TMP_ok", "OK")
        self.assertEqual(du.getSemaphore("TMP_ok"), "OK")
        self.assertEqual(self.__log.getvalue(), "")

    def testGetSemaphoreEmptyFile(self) -> None:
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=False, log=self.__log)
        open(os.path.join(self.__sessionPath, "TMP_empty"), "w").close()
        self.assertEqual(du.getSemaphore("TMP_empty"), "FAIL")

    def testRunDetachSuccess(self) -> None:
        sph = self.__runWorker("succeed", siteId="MYSITE")
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=False, log=self.__log)
        self.assertEqual(du.getSemaphore(sph), "OK")
        with open(self.__outPath) as fin:
            self.assertEqual(fin.read(), "site=MYSITE\n")
        childLog = self.__readChildLog(sph)
        self.assertIn("Worker succeeded", childLog)
        self.assertIn("Child Process: PID#", childLog)
        self.assertIn("Site id       MYSITE", childLog)
        parentLog = self.__log.getvalue()
        self.assertIn("STARTING", parentLog)
        self.assertIn("PARENT COMPLETED", parentLog)

    def testRunDetachFailure(self) -> None:
        sph = self.__runWorker("fail")
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=False, log=self.__log)
        self.assertEqual(du.getSemaphore(sph), "FAIL")
        self.assertFalse(os.path.exists(self.__outPath))

    def testRunDetachException(self) -> None:
        sph = self.__runWorker("explode")
        du = DetachUtils(FakeRequest(self.__sessionPath), verbose=False, log=self.__log)
        self.assertEqual(du.getSemaphore(sph), "FAIL")
        childLog = self.__readChildLog(sph)
        self.assertIn("ValueError: Worker exploded", childLog)
        self.assertIn("Failing for child Process", childLog)

    def testRunDetachQuiet(self) -> None:
        reqObj = FakeRequest(self.__sessionPath)
        du = DetachUtils(reqObj, verbose=False, log=self.__log)
        self.assertTrue(du.set(workerObj=Worker(self.__outPath), workerMethod="succeed"))
        self.assertTrue(du.runDetach())
        sph = reqObj.getValue("semaphore")
        self.assertTrue(self.__waitForSemaphore(du, sph))
        self.assertEqual(self.__log.getvalue(), "")
        self.assertNotIn("Child Process", self.__readChildLog(sph))


class RedirectDeviceTests(unittest.TestCase):
    @staticmethod
    def testWriteDiscards() -> None:
        dev = RedirectDevice()
        dev.write("anything")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
