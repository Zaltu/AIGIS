"""
Representation of a plugin with handlers used by the core to properly route traffic.
"""

class AigisPlugin():
    """
    A plugin that can be managed by AIGIS and it's core.

    :param str name: name of the plugin
    :param str root: root path of the plugin
    :param str ptype: the plugin type
    :param bool restart: whether an auto-restart should be attempted on death
    :param object config: the plugin's config namespace
    :param LogManager log_manager: the log manager for this AIGIS instance
    """
    def __init__(self, name, root, log_manager, ptype=None, restart=False, config=None):
        self.id = id(self)
        self.name = name
        self.root = root
        self.type = ptype
        self.restart = restart
        self.config = config
        self.log = log_manager.hook(self)
        self.log.boot("Registered plugin...")

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
