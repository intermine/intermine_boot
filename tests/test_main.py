import unittest
import os

class TestLocalBuild(unittest.TestCase):

    def test_version(self):
        exit_status = os.system('intermine_boot --version')

        self.assertEqual(exit_status, 0)
