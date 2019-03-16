##
# File: DetachUtilsTests.py
# Date:  09-May-2019  E. Peisach
#
# Updates:
##
"""Test cases for DetachUtils functionality"""

import sys
import os
import time
import platform
import unittest

from wwpdb.utils.detach.DetachUtils import DetachUtils
try:
    from wwpdb.utils.session.WebRequest import InputRequest
    skiptest = False
except ImportError:
    # For PyCharm error handling
    class InputRequest(object):
        pass
    skiptest = True


@unittest.skipIf(skiptest, "Requires wwpdb.utils.session for testing")
class DetachUtilTest(unittest.TestCase):
    def setUp(self):
        here = os.path.abspath(os.path.dirname(__file__))
        testoutput = os.path.join(here, 'test-output', platform.python_version())
        if not os.path.exists(testoutput):
            os.makedirs(testoutput)
        self.__outputfile = os.path.join(testoutput, 'detachtest')
        if os.path.exists(self.__outputfile):
            os.unlink(self.__outputfile)
        self.__sessiondir = os.path.join(testoutput, 'sessions')
        if not os.path.exists(self.__sessiondir):
            os.makedirs(self.__sessiondir)
        self.__sessiontop = testoutput

    def _runTest(self):
        time.sleep(3)
        with open(self.__outputfile, 'w') as fout:
            fout.write("Passed\n")
        return "Good"

    def setLogHandle(self, log=sys.stderr):
        """  Reset the stream for logging output. Requirement for DetachUtils
        """
        try:
            self.__lfh = log
            return True
        except IOError:
            return False
        #

    def testRun(self):
        """Tests creation of a detached util"""
        params = {"TopSessionPath": [self.__sessiontop]}
        reqobj = InputRequest(params)

        reqobj.printIt()

        du = DetachUtils(reqobj, verbose=True)
        du.set(workerObj=self, workerMethod="_runTest")
        du.runDetach()
        sph = reqobj.getValue('semaphore')
        print("Semaphore %s" % sph)

        cntmax = 10
        cnt = 0
        for cnt in range(cntmax):
            if du.semaphoreExists(sph):
                break
            time.sleep(1)
            print("SLEEP %s" % cnt)

        self.assertNotEqual(cnt, cntmax - 1, "Count exceeded")
        self.assertTrue(du.semaphoreExists(sph), "Semaphore file missing")
        val = du.getSemaphore(sph)
        self.assertEqual(val, 'OK', '')


if __name__ == '__main__':
    unittest.main()
