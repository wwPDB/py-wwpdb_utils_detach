##
# File: WebServiceImportTests.py
# Date:  06-Oct-2018  E. Peisach
#
# Updates:
##
"""Test cases for webservice - simply import everything to ensure imports work"""

__docformat__ = "restructuredtext en"
__author__ = "Ezra Peisach"
__email__ = "peisach@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.01"

import unittest

from wwpdb.utils.detach.DetachUtils import DetachUtils
from wwpdb.utils.detach.DetachedProcessBase import DetachedProcessBase
from wwpdb.utils.detach.SubProcessUtil import SubProcessUtil


class ImportTests(unittest.TestCase):
    def setUp(self):
        pass

    def testInstantiate(self):
        # Needs a reqobj
        #vc = DetachUtils()
        vc = DetachedProcessBase()
        vc = SubProcessUtil()

if __name__ == '__main__':
    unittest.main()


    
