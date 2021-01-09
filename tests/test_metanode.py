import json
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

    def test_new(self):
        self.assertFalse(cmds.objExists("transform2"))
        MetaNode.new("transform")
        self.assertTrue(cmds.objExists("transform2"))
        cmds.delete("transform2")
        self.assertFalse(cmds.objExists("transform2"))

    def test_special_new_type(self):
        class NewMetaNode(MetaNode):
            pass

        node = cmds.createNode("transform")
        cmds.addAttr(node, longName="metanode_type", dataType="string")
        cmds.setAttr("{}.metanode_type".format(node), "NewMetaNode", type="string")

        rig = MetaNode(node)

        self.assertTrue(isinstance(rig, NewMetaNode))

    def test_fails_on_non_string_init(self):
        with self.assertRaises(TypeError) as context:
            MetaNode(self.meta_node)
        self.assertTrue("node name" in str(context.exception))

    def test_fails_on_non_existing_node(self):
        with self.assertRaises(ValueError) as context:
            MetaNode("transform2")
        self.assertTrue("does not exist" in str(context.exception))

    def test_add_default_fields(self):
        node = cmds.createNode("transform")

        default_field_names = ["metanode_fields", "metanode_type", "is_initialized"]

        for field_name in default_field_names:
            has_field = cmds.attributeQuery(field_name, node="transform2", exists=True)
            self.assertFalse(has_field)

        MetaNode(node)

        for field_name in default_field_names:
            has_field = cmds.attributeQuery(field_name, node="transform2", exists=True)
            self.assertTrue(has_field)

    def test_add_field_updates_metanode_fields(self):
        self.meta_node.add_field(IntValidator, "my_count", Accessibility.private)

        self.meta_node.write_fields()
        metanode_fields_raw = cmds.getAttr("transform1.metanode_fields")
        fields_data = json.loads(metanode_fields_raw)

        self.assertTrue("my_count" in fields_data)
        self.assertEqual(
            fields_data["my_count"],
            {
                "accessibility": 1,
                "multi": False,
                "validator": "IntValidator",
            },
        )

    def test_serialize(self):
        expected_data = {
            "metanode_fields": {
                "metanode_fields": {
                    "accessibility": 1,
                    "multi": False,
                    "validator": "JsonValidator",
                },
                "metanode_type": {
                    "accessibility": 1,
                    "multi": False,
                    "validator": "StringValidator",
                },
                "is_initialized": {
                    "accessibility": 1,
                    "multi": False,
                    "validator": "BoolValidator",
                },
            },
            "metanode_type": "MetaNode",
            "is_initialized": True,
        }

        self.meta_node.write_fields()
        data = self.meta_node.serialize()
        data.pop("uuid")

        self.assertDictEqual(data, expected_data)

    def test_name(self):
        self.assertEqual(self.meta_node.name(), "transform1")

        cmds.rename("transform1", "transform2")

        self.assertEqual(self.meta_node.name(), "transform2")

    def test_path(self):
        self.assertEqual(self.meta_node.path(), "|transform1")

        cmds.group("transform1")

        self.assertEqual(self.meta_node.path(), "|group1|transform1")

    def test_uuid(self):
        self.assertEqual(self.meta_node.uuid(), cmds.ls("transform1", uuid=True)[0])

    def test_same_instance(self):
        other_metanode = MetaNode(self.meta_node.path())
        self.assertTrue(self.meta_node is other_metanode)

    def test_write_field(self):
        self.meta_node.add_field(IntValidator, "my_count", Accessibility.private)
        self.meta_node.my_count.set(10)
        self.assertTrue(cmds.getAttr("{}.my_count".format(self.meta_node)) == 0)
        self.meta_node.write_fields()
        self.assertTrue(cmds.getAttr("{}.my_count".format(self.meta_node)) == 10)
