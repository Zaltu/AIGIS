"""
Representation of a plugin with handlers used by the core to properly route traffic.
"""

class AigisPlugin():
    """
    A plugin that can be managed by AIGIS and it's core.

    :param str name: name of the plugin
    :param str root: root path of the plugin
    :param str ptype: the plugin type
    """
    def __init__(self, name, root, ptype):
        self.id = id(self)
        self.name = name
        self.root = root
        self.type = ptype

    def __eq__(self, other):
        """
        Determine if two plugins are the same based on their attributed UID.
        This only works between two AigisPlugin objects. Otherwise will return false.

        :param AigisPlugin other: other plugin against which to check

        :returns: boolead equivalence
        :rtype: bool
        """
        try:
            return self.id == other.id
        except AttributeError:
            pass
        return False

    def cleanup(self):
        """
        Container function to handle cleaning up any resources used by the plugin.
        By default does nothing. Should be overwritten if cleanup is required.
        """
