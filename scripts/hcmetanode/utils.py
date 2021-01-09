import maya.api.OpenMaya as om2
import maya.cmds as cmds


def get_uuid(mobject):
    """Return a `maya.api.OpenMaya.MObject` UUID.

    Args:
        mobject (maya.api.OpenMaya.MObject): MObject to get the UUID of.

    Returns:
        str: The MObject UUID.
    """
    return om2.MFnDependencyNode(mobject).uuid().asString()


def set_uuid(mobject, uuid):
    """Set a `maya.api.OpenMaya.MObject` UUID.

    Args:
        mobject (maya.api.OpenMaya.MObject): MObject to set the UUID of.
        uuid (str): UUID to set on the MObject

    Raises:
        ValueError: If the UUID is not formatted as a valid Maya UUID.
        # TODO: Use a different error type.
        ValueError: If the UUID is already taken.
    """
    pattern = re.compile(
        r"[A-Z0-9]{8}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{12}"
    )
    if not pattern.match(uuid):
        raise ValueError("'{}' is not a valid UUID".format(uuid))

    existing_node = cmds.ls(uuid)
    if existing_node:
        raise ValueError(
            "The uuid '{}' is already assigned to the node {}".format(
                uuid, existing_node[0]
            )
        )

    uuid = om2.MUuid(uuid)
    om2.MFnDependencyNode(mobject).setUuid(uuid)


def get_mobject(node):
    """Return a `maya.api.OpenMaya.MObject` from a node name.

    Args:
        node (str): Name of the node.
            It should be unique as it is forwarded to
            `maya.api.OpenMaya.MSelectionList.add`.

    Returns:
        maya.api.OpenMaya.MObject: The underlying MObject.
    """
    sel_list = om2.MSelectionList()
    sel_list.add(node)
    mobject = sel_list.getDependNode(0)
    return mobject


def get_mplug(attribute):
    """Return a `maya.api.OpenMaya.MPlug` from a node attribute.

    Args:
        node (str): Name of the attribute.
            It is formatted as `{node_name}.{attribute_name}`.
            It should be unique as it is forwarded to
            `maya.api.OpenMaya.MSelectionList.add`.

    Returns:
        maya.api.OpenMaya.MPlug: The underlying MPlug.
    """
    sel_list = om2.MSelectionList()
    sel_list.add(attribute)
    mobject = sel_list.getPlug(0)
    return mobject


def all_subclasses(cls):
    """Recursively find subclasses of a class.

    The subclasses should already be imported for this function to work properly.

    Args:
        cls (type): Class to inspect.

    Returns:
        set[type]: The set of subclasses.
    """
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )
