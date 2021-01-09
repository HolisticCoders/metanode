from __future__ import absolute_import, with_statement

import logging
import traceback
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager

import maya.cmds as cmds

from .enum import Enum
from .utils import get_mplug

logger = logging.getLogger(__name__)


class Accessibility(Enum):
    """Accessibility of a field.

    Public fields are meant to be interactive, and modified by the user.
    They are single value Maya attributes, exposed in the channel box, and
    are not locked by `sauron`.

    Private fields however, can be any type of Maya attribute (including multi
    attributes), are locked, and only written to Maya at the end of a build script.
    """

    private = 1
    public = 2


def get_field_class(accessibility, multi):
    """Return a field class for a set of features.

    Args:
        accessibility (Accessibility): Whether the field should be public or private.
        multi (bool): Whether the field should be an array attribute, or a single
            value one.

    Returns:
        Type[FieldBase]: A field class corresponding to the expected behavior.

    Raises:
        ValueError: If a multi field is asked, with a public accessibility.
            A public field cannot be made public.
    """
    if multi:
        if accessibility == Accessibility.private:
            return MultiField
        else:
            raise ValueError("A multi field cannot be public.")
    else:
        return PublicField if accessibility == Accessibility.public else Field


class FieldBase(object):
    """Base class for Fields defining the common interface for all Fields.

    A Field is a Wrapper on a maya attribute that does three things:
    1. When setting, convert the value to something that can be stored in the attribute.
    2. When getting, convert the value
    3. Ensures the data in the attribute is serializable

    Fields are very generic classes that don't make assumptions about the underlying attributes.
    All the data manipulation is done through a `FieldValidator`

    Args:
        validator_class (FieldValidator): Type of validator to use.
        metanode (MetaNode): MetaNode to create the field on.
        name (str): Name of the Maya attribute.
        default_value (optional): Default value for this field.
        **kwargs: Additional arguments for the underlying `maya.cmds.addAttr` call.

    Attributes:
        validator_class (FieldValidator): Type of validator to use.
        metanode (MetaNode): MetaNode to create the field on.
        name (str): Name of the Maya attribute.
        value: Current value of the field.
            This is the value used throughout the script ; it gets written to Maya
            once all operations are done.
        mplug (maya.api.OpenMaya.MPlug): Handle to the MPlug instance.
    """

    __metaclass__ = ABCMeta

    def __init__(self, validator_class, metanode, name, default_value=None, **kwargs):
        self.validator = validator_class
        self.create_attribute_kwargs = self.validator.process_kwargs(**kwargs)
        self.metanode = metanode
        self.name = name
        self._value = (
            default_value
            if default_value is not None
            else validator_class.get_default_value()
        )

        self.create_attribute()

        self.mplug = get_mplug(self.path())

        self.read()

    def path(self):
        """Return the full path of the maya attribute.

        Returns:
            str: Full path of the Maya attribute.
        """
        return "{path}.{name}".format(path=self.metanode.path(), name=self.name)

    @abstractmethod
    def create_attribute(self):
        """Create the maya attribute.

        Returns:
            bool: ``True`` if the attribute was created, ``False`` if it already
                existed.
        """

    @abstractmethod
    def get(self):
        """Return the field value."""

    @abstractmethod
    def set(self, value):
        """Set the field value."""

    @abstractmethod
    def read(self):
        """Read the field value from Maya."""

    @abstractmethod
    def write(self):
        """Write the field value to Maya."""

    def serialize(self):
        """Serialize the field value to a JSON compatible value."""
        return self.validator.serialize(self.get())

    @contextmanager
    def _protect_attribute(self):
        cmds.setAttr(self.path(), lock=False)

        yield

        cmds.setAttr(self.path(), lock=True)


class SingleFieldBase(FieldBase):  # pylint: disable=abstract-method
    """Field class used for "single" attributes."""

    __metaclass__ = ABCMeta

    def create_attribute(self):
        if not cmds.attributeQuery(self.name, node=self.metanode.path(), exists=True):

            cmds.addAttr(
                self.metanode.path(),
                longName=self.name,
                keyable=False,
                **self.create_attribute_kwargs
            )

            return True

        return False


class Field(SingleFieldBase):
    """Field class used for private "single" attributes."""

    def get(self):
        """Return the field value."""
        return self._value

    def set(self, value):
        """Set the field value."""
        self._value = value

    def write(self):
        try:
            value = self.validator.to_attribute(self._value)
        except Exception as error:
            logger.debug(traceback.format_exc())
            logger.warning(error)
        else:
            with self._protect_attribute():
                if cmds.listConnections(self.path(), source=True, destination=False):
                    return
                cmds.setAttr(self.path(), value, **self.validator.set_attribute_kwargs)

    def read(self):
        value = cmds.getAttr(self.path())
        if value is None:
            return
        self._value = self.validator.from_attribute(value)


class PublicField(Field):
    """Field class used for public "single" attributes."""

    def create_attribute(self):
        if super(PublicField, self).create_attribute():
            cmds.setAttr(self.path(), edit=True, channelBox=True)
            return True
        return False

    def get(self):
        """Return the field value from Maya."""
        return self.read()

    def set(self, value):
        """Write the field value to Maya."""
        self._value = value
        self.write()

    @contextmanager
    def _protect_attribute(self):
        """Never lock a public field."""
        yield


class MultiField(FieldBase):  # pylint: disable=abstract-method
    """Field class used for private "multi" attributes."""

    def __init__(self, validator_class, metanode, name, default_value=None, **kwargs):
        if default_value is None:
            default_value = []
        super(MultiField, self).__init__(
            validator_class, metanode, name, default_value, **kwargs
        )

    def create_attribute(self):
        if not cmds.attributeQuery(self.name, node=self.metanode.path(), exists=True):

            cmds.addAttr(
                self.metanode.path(),
                longName=self.name,
                multi=True,
                keyable=False,
                **self.create_attribute_kwargs
            )

            return True

        return False

    def get(self):
        """Return the field value."""
        return self._value

    def set(self, value):
        """Set the field value."""
        self._value = value

    def write(self):
        value = self._value

        with self._protect_attribute():

            self._clear_maya_attribute()

            for i, index_value in enumerate(value):

                index_value = self.validator.to_attribute(index_value)
                cmds.setAttr(
                    "{path}[{i}]".format(path=self.path(), i=i),
                    index_value,
                    **self.validator.set_attribute_kwargs
                )

    def read(self):
        result = []
        for attr in self._iter_elements():
            value = self.validator.from_attribute(cmds.getAttr(attr))
            result.append(value)

        self._value = result

    def serialize(self):
        value = self.get()
        if value:
            return self.validator.serialize(value)
        else:
            return []

    def clear(self):
        self._clear_python_attribute()
        self._clear_maya_attribute()

    def _clear_python_attribute(self):
        self._value = []

    def _clear_maya_attribute(self):
        cmds.setAttr(self.path(), lock=False)

        for attr in self._iter_elements():
            cmds.setAttr(attr, lock=False)

        cmds.removeMultiInstance(self.path(), allChildren=True, b=True)

    @contextmanager
    def _protect_attribute(self):
        for attr in self._iter_elements():
            cmds.setAttr(attr, lock=False)

        yield

        for attr in self._iter_elements():
            cmds.setAttr(attr, lock=True)

    def _iter_elements(self):
        for index in xrange(self.mplug.numElements()):
            plug = self.mplug.elementByLogicalIndex(index)
            yield plug.name()
