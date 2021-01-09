from __future__ import absolute_import

import unittest

import maya.api.OpenMaya as om2
import maya.cmds as cmds

from hcmetanode.fields import Accessibility
from hcmetanode.metanode import MetaNode
from hcmetanode.validators import (
    BoolValidator,
    EnumValidator,
    FloatValidator,
    IntValidator,
    MatrixValidator,
    MetaNodeValidator,
    StringValidator,
)

# TODO: Test JsonValidator


class TestValidators(unittest.TestCase):
    def setUp(self):
        cmds.file(new=True, force=True)

        node_name = cmds.createNode("transform")
        self.meta_node = MetaNode(node_name)

    def test_int_validator(self):
        self.meta_node.add_field(IntValidator, "jointCount", Accessibility.private)
        self.meta_node.jointCount.set(10)

        self.meta_node.jointCount.write()
        self.assertEqual(cmds.getAttr("transform1.jointCount"), 10)

        self.meta_node.jointCount.read()
        self.assertEqual(self.meta_node.jointCount.get(), 10)

    def test_float_validator(self):
        self.meta_node.add_field(FloatValidator, "armLength", Accessibility.private)
        self.meta_node.armLength.set(10)

        self.meta_node.armLength.write()
        self.assertEqual(cmds.getAttr("transform1.armLength"), 10)

        self.meta_node.armLength.read()
        self.assertEqual(self.meta_node.armLength.get(), 10)

    def test_float_validator_translate_x(self):
        self.meta_node.add_field(FloatValidator, "translateX", Accessibility.private)
        self.meta_node.translateX.set(10)

        self.meta_node.translateX.write()
        self.assertEqual(cmds.getAttr("transform1.translateX"), 10)

        self.meta_node.translateX.read()
        self.assertEqual(self.meta_node.translateX.get(), 10)

    def test_bool_validator(self):
        self.meta_node.add_field(BoolValidator, "isItTrue", Accessibility.private)
        self.meta_node.isItTrue.set(False)
        self.meta_node.isItTrue.get()
        self.assertEqual(cmds.getAttr("transform1.isItTrue"), 0)
        self.assertEqual(self.meta_node.isItTrue.get(), False)

    def test_string_validator(self):
        self.meta_node.add_field(StringValidator, "my_name_is", Accessibility.private)
        self.meta_node.my_name_is.set("Jeff")
        self.meta_node.my_name_is.write()
        self.assertEqual(cmds.getAttr("transform1.my_name_is"), "Jeff")
        self.meta_node.my_name_is.read()
        self.assertEqual(self.meta_node.my_name_is.get(), "Jeff")

    def test_matrix_validator(self):
        self.meta_node.add_field(MatrixValidator, "rest_matrix", Accessibility.private)
        self.meta_node.rest_matrix.set(
            # fmt: off
            om2.MMatrix([
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                1, 2, 3, 1,
            ])
            # fmt: on
        )
        self.meta_node.rest_matrix.write()
        self.assertEqual(
            cmds.getAttr("transform1.rest_matrix"),
            # fmt: off
            [
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                1, 2, 3, 1,
            ],
            # fmt: on
        )

        self.meta_node.rest_matrix.read()
        self.assertEqual(
            self.meta_node.rest_matrix.get(),
            # fmt: off
            om2.MMatrix([
                1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0,
                1, 2, 3, 1,
            ])
            # fmt: on
        )

    def test_enum_validator(self):
        class Axes(object):
            X = 0
            Y = 1
            Z = 2

        self.meta_node.add_field(
            EnumValidator,
            "upAxis",
            Accessibility.private,
            choices=["X", "Y", "Z"],
        )
        self.meta_node.upAxis.set(Axes.X)
        self.assertEqual(cmds.getAttr("transform1.upAxis"), Axes.X)
        self.assertEqual(self.meta_node.upAxis.get(), Axes.X)

    def test_meta_node_validator(self):
        node_name2 = cmds.createNode("transform")
        meta_node2 = MetaNode(node_name2)
        self.meta_node.add_field(MetaNodeValidator, "other_node", Accessibility.private)
        self.meta_node.other_node.set(meta_node2)

        self.meta_node.other_node.write()
        self.assertEqual(cmds.getAttr("transform1.other_node"), meta_node2.uuid())

        self.meta_node.other_node.read()
        self.assertEqual(self.meta_node.other_node.get().uuid(), meta_node2.uuid())

    def test_add_multi_field(self):
        self.meta_node.add_field(
            IntValidator,
            "indices",
            Accessibility.private,
            multi=True,
        )
        self.meta_node.indices.set([0, 1, 2, 3])

        self.meta_node.indices.write()
        self.assertEqual(
            # Please don't ask.
            # Ok, Maya returned floats in a tuple in a list. Sad face is sad.
            [int(index) for index in cmds.getAttr("transform1.indices")[0]],
            [0, 1, 2, 3],
        )

        self.meta_node.indices.read()
        self.assertEqual(self.meta_node.indices.get(), [0, 1, 2, 3])

    def test_multi_field_clear(self):
        self.meta_node.add_field(
            IntValidator,
            "indices",
            Accessibility.private,
            multi=True,
        )
        self.meta_node.indices.set([0, 1, 2, 3])
        self.assertEqual(self.meta_node.indices.get(), [0, 1, 2, 3])
        self.meta_node.indices.clear()
        self.assertEqual(self.meta_node.indices.get(), [])
