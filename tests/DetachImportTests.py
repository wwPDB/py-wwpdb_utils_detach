##
# File: DetachImportTests.py
# Date:  06-Oct-2018  E. Peisach
#
# Updates:
##
"""Test cases for DetachUtils - simply import everything to ensure imports work"""

import unittest

# from wwpdb.utils.detach.DetachUtils import DetachUtils
from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase
from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil


class ImportTests(unittest.TestCase):
    def setUp(self):
        pass

    def testInstantiate(self):
        # Needs a reqobj
        # vc = DetachUtils()
        DetachedProcessBase()
        SubProcessUtil()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
