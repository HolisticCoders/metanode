from __future__ import absolute_import

import json

import maya.api.OpenMaya as om2
import maya.cmds as cmds

from .metanode import MetaNode


class FieldValidator(object):
    """Base class for all field validators.

    A Field Validator ensures the data passed to and from the maya is of the proper type.

    Validators are never instantiated but have static and classmethods
    that are used by the Field to process the attribute's data.

    The create_attribute_kwargs and set_attribute_kwargs are passed to maya's addAttr
    and setAttr commands by the Field.
    """

    create_attribute_kwargs = {}
    set_attribute_kwargs = {}

    @staticmethod
    def from_attribute(value):
        """Cast the Maya attribute return ``value`` to a Python friendly value.

        Args:
            value: Maya attribute value, as returned by `maya.cmds.getAttr`.

        Returns:
            Original value casted to a more user-friendly type for some validators.

            Default implementation returns the Maya attribute value.
        """
        return value

    @staticmethod
    def to_attribute(value):
        """Cast the field ``value`` to a Maya compliant attribute value.

        Args:
            value: Field value.

        Returns:
            Original value casted to a Maya compliant value, to forward to
            `maya.cmds.setAttr`.

            Default implementation returns the field value.
        """
        return value

    @classmethod
    def process_kwargs(cls, **kwargs):
        """Cast the field ``create_attribute_kwargs`` to a Maya compliant value.

        Args:
            **kwargs: Additional keyword arguments for the `maya.cmds.addAttr` call.

        Returns:
            Original value casted to a Maya compliant value, to forward to
            `maya.cmds.addAttr`.

            Default implementation returns the field class ``create_attribute_kwargs``
                value.
        """
        return cls.create_attribute_kwargs

    @staticmethod
    def serialize(value):
        """Serialize the `FieldValidator` to a JSON serializable object.

        Returns:
            dict: A dict representation of the `FieldValidator`.
        """
        return value

    @staticmethod
    def get_default_value():
        return None


class IntValidator(FieldValidator):
    create_attribute_kwargs = {"attributeType": "long"}

    @staticmethod
    def to_attribute(value):
        return int(value)

    @staticmethod
    def get_default_value():
        return 0


class FloatValidator(FieldValidator):
    create_attribute_kwargs = {"attributeType": "double"}

    @staticmethod
    def to_attribute(value):
        return float(value)

    @staticmethod
    def get_default_value():
        return 0.0


class BoolValidator(FieldValidator):
    create_attribute_kwargs = {"attributeType": "bool"}

    @staticmethod
    def to_attribute(value):
        return bool(value)

    @staticmethod
    def get_default_value():
        return False


class StringValidator(FieldValidator):
    create_attribute_kwargs = {"dataType": "string"}
    set_attribute_kwargs = {"type": "string"}

    @staticmethod
    def to_attribute(value):
        return str(value)

    @staticmethod
    def get_default_value():
        return ""


class MatrixValidator(FieldValidator):
    """Returns an MMatrix and serializes as a flat list"""

    create_attribute_kwargs = {"dataType": "matrix"}
    set_attribute_kwargs = {"type": "matrix"}

    @staticmethod
    def from_attribute(value):
        return om2.MMatrix(value)

    @staticmethod
    def serialize(value):
        # fmt: off
        return [
            value[0],  value[1],  value[2],  value[3],
            value[4],  value[5],  value[6],  value[7],
            value[8],  value[9],  value[10], value[11],
            value[12], value[13], value[14], value[15],
        ]
        # fmt: on

    @staticmethod
    def get_default_value():
        return om2.MMatrix()


class EnumValidator(FieldValidator):
    """Validator for enum values.

    When using `MetaNode.add_field`, you must provide a ``choices`` argument.

    This is a `list[str]` argument defining all enum values.

    It will be forwarded to `maya.cmds.addAttr` as ``enumNames``, joining
    all elements of the list with ``:``.
    """

    create_attribute_kwargs = {"attributeType": "enum"}

    @classmethod
    def process_kwargs(cls, **kwargs):
        create_attribute_kwargs = cls.create_attribute_kwargs.copy()
        choices = kwargs.pop("choices", [])
        create_attribute_kwargs["enumName"] = ":".join(choices) + ":"

        return create_attribute_kwargs


class MetaNodeValidator(StringValidator):
    """Stores and serializes the MetaNode as a uuid, returns a MetaNode."""

    @staticmethod
    def to_attribute(value):
        return value.uuid() if value else ""

    @staticmethod
    def from_attribute(value):
        if not value:
            return None

        res = cmds.ls(value)

        if res:
            node = MetaNode(res[0])
            return node

        return None

    @staticmethod
    def serialize(value):
        if value:
            return value.uuid()
        return None

    @staticmethod
    def get_default_value():
        return None


class JsonValidator(StringValidator):
    @staticmethod
    def to_attribute(value):
        if value is None:
            value = {}
        return json.dumps(value)

    @staticmethod
    def from_attribute(value):
        if value is None:
            value = "{}"
        return json.loads(value)

    @staticmethod
    def get_default_value():
        return {}
