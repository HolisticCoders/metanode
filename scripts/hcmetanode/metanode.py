import maya.api.OpenMaya as om2
import maya.cmds as cmds

from .fields import Accessibility, get_field_class
from .utils import all_subclasses, get_mobject, get_uuid


class MetaNode(object):
    """Wrapper over a Maya node ensuring serialization.

    The MetaNode keeps a reference to the API MObject

    Args:
        node (str): Name of the Maya node to wrap.
            It should be a unique name, as it is forwarded to
            `maya.api.OpenMaya.MSelectionList.add`.

    Attributes:
        mobject (maya.api.OpenMaya.MObject): Handle to Maya's MObject.
        fields (dict[str, FieldBase]): Fields of this MetaNode.
    """

    _instances = {}

    def __new__(cls, node):
        """Re-instantiate the proper MetaNode subclass if the node has already been a MetaNode in its lifetime."""
        if not isinstance(node, basestring):
            raise TypeError("MetaNode can only be instanciated from a node name.")

        if not cmds.objExists(node):
            raise ValueError(
                "Specified Maya node {} does not exist; "
                "`MetaNode.new` can be used to create a node along with the MetaNode".format(
                    node
                )
            )

        uuid = get_uuid(get_mobject(node))
        instance = MetaNode._instances.get(uuid)
        if instance:
            return instance

        if cmds.attributeQuery("metanode_type", node=node, exists=True):
            stored_class_name = cmds.getAttr("{}.metanode_type".format(node))
        else:
            stored_class_name = cls.__name__

        class_to_instantiate = None

        if stored_class_name == cls.__name__:
            class_to_instantiate = cls
        else:
            for subclass in all_subclasses(cls):
                if stored_class_name == subclass.__name__:
                    class_to_instantiate = subclass

        if class_to_instantiate is None:
            raise Exception(
                "The class name `{stored_class_name}` stored on the node {node}"
                " wasn't found in {name}'s subclasses".format(
                    stored_class_name=stored_class_name,
                    node=node,
                    name=cls.__name__,
                )
            )

        return super(MetaNode, cls).__new__(class_to_instantiate)

    def __init__(self, node):
        self.mobject = get_mobject(node)

        self.fields = {}

        self.add_default_fields()

        if self.uuid() not in MetaNode._instances:
            self.read_fields()
            MetaNode._instances[self.uuid()] = self

        if not self.is_initialized.get():
            self.initialize()
            self.is_initialized.set(True)

    @classmethod
    def new(cls, *args, **kwargs):
        """Create a new MetaNode along with a new maya node.

        Subclasses should override this method to create the according maya node.

        Args:
            args and kwargs are passed as is to cmds.createNode()
        """
        return cls(cmds.createNode(*args, **kwargs))

    @classmethod
    def from_uuid(cls, uuid):
        """Create a MetaNode from a Maya UUID.

        Args:
            uuid (str): UUID of the node in the current scene.

        Returns:
            MetaNode: New MetaNode around the given UUID.
        """
        node = cmds.ls(uuid)
        if not node:
            raise ValueError("No node with uuid '{}'".format(uuid))
        return MetaNode.__new__(cls, node[0])

    def initialize(self):
        """Initialize the MetaNode.

        This is only called the first time the node is instanciated as a MetaNode
        The MetaNode class doesn't actually implement this but subclasses can use this as they need.
        """

    def add_default_fields(self):
        """Create all the Fields needed by this `MetaNode`.

        Subclasses can override this to add their own fields.
        All new fields should be added after the call to super()
        """
        from .validators import (
            BoolValidator,
            FieldValidator,
            JsonValidator,
            StringValidator,
        )

        self.add_field(JsonValidator, "metanode_fields", Accessibility.private)

        for field_name, field_data in self.metanode_fields.get().items():
            validator_name = field_data.pop("validator")
            accessibility = Accessibility(field_data.pop("accessibility"))
            multi = field_data.pop("multi")
            for validator_cls in all_subclasses(FieldValidator):
                if validator_cls.__name__ == validator_name:
                    self.add_field(
                        validator_cls, field_name, accessibility, multi, **field_data
                    )

        self.add_field(StringValidator, "metanode_type", Accessibility.private)
        self.metanode_type.set(self.__class__.__name__)

        self.add_field(BoolValidator, "is_initialized", Accessibility.private)

    def add_field(self, validator, name, accessibility, multi=False, **kwargs):
        """Add a new field to this MetaNode.

        Args:
            validator (FieldValidator): Validator for the new field.
            name (str): Name of the field, and underlying Maya attribute.
            accessibility (Accessibility): Accessibility of the field.
                If the field is declared `Accessibility.public`, then users
                will be able to modify it in real time from Maya.
                Otherwise, the field will be hidden from the user and used
                internally by its `MetaNode` owner.
            multi (bool, optional): Whether this field should be a `MultiField`,
                and a multi attribute in Maya.
            **kwargs: Additional arguments for the `Field` or `MultiField`
                constructor and underlying `maya.cmds.addAttr` call.
        """
        field_cls = get_field_class(accessibility, multi)
        field = field_cls(validator, self, name, **kwargs)

        self.fields[name] = field

        field_data = {
            "validator": validator.__name__,
            "multi": multi,
            "accessibility": accessibility.value,
        }
        field_data.update(kwargs)

        self.metanode_fields.get()[name] = field_data

        return field

    def read_fields(self):
        """Load the maya attributes in memory."""
        for field in self.fields.itervalues():
            field.read()

    def write_fields(self):
        """write the python attributes stored in memory to the maya attribtute."""
        for field in self.fields.itervalues():
            field.write()

    def serialize(self):
        """Serialize the `MetaNode` to a JSON serializable object.

        Returns:
            dict: A dict representation of the `MetaNode`.
        """
        data = {}
        data["uuid"] = self.uuid()
        for name, field in self.fields.items():
            data[name] = field.serialize()
        return data

    def name(self):
        """Return the short name of this MetaNode.

        If passing the metanode to a maya.cmds command,
        use MetaNode.path() instead.

        Returns:
            str: Short name of this `MetaNode`.
        """
        return om2.MFnDependencyNode(self.mobject).name()

    def path(self):
        """Return the full DAG Path of this MetaNode.

        Returns:
            str: Full path of this `MetaNode`.
        """
        if self.mobject.hasFn(om2.MFn.kDagNode):
            return om2.MFnDagNode(self.mobject).getPath().fullPathName()
        else:
            return self.name()

    def uuid(self):
        """Returns the Maya's scene UUID of the underlying node.

        Returns:
            str: UUID of the underlying Maya node.
        """
        return get_uuid(self.mobject)

    def __getattr__(self, name):
        """Get the fields of this MetaNode."""
        field = self.fields.get(name)
        if field is not None:
            return field
        return None

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.name())

    def __str__(self):
        return self.path()

    def __eq__(self, other):
        return self.uuid() == other.uuid()
