from __future__ import absolute_import, with_statement

import unittest

import maya.cmds as cmds

from hcmetanode.fields import Accessibility
from hcmetanode.metanode import MetaNode
from hcmetanode.validators import IntValidator


class TestMetaNode(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, force=True)

        node_name = cmds.createNode("transform")
        self.meta_node = MetaNode(node_name)

    def test_public_is_unlocked(self):
        self.meta_node.add_field(IntValidator, "my_field", Accessibility.public)
        self.assertFalse(cmds.getAttr(self.meta_node.my_field.path(), lock=True))

    def test_public_is_unlocked_after_set(self):
        self.meta_node.add_field(IntValidator, "my_field", Accessibility.public)

        self.meta_node.my_field.set(10)

        self.assertFalse(cmds.getAttr(self.meta_node.my_field.path(), lock=True))
