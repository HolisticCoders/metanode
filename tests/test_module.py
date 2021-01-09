import unittest

import maya.cmds as cmds


class TestModule(unittest.TestCase):
    def test_module_loaded(self):
        module_loaded = "hc-metanode" in cmds.moduleInfo(listModules=True)
        self.assertTrue(module_loaded)
