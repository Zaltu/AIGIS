"""
Helper module to hold and organize loaded plugins.
"""

class PluginManager(list):
    """
    Helper clas to hold and organize loaded plugins.
    """
    core = []
    external = []
    dead = []
    def __init__(self):
        list.__init__(self)

    def add_to_core(self, plugin):
        """
        Add an AigisPlugin to this list, but also to the core list.

        :param AigisPlugin plugin: plugin object to add
        """
        self.core.append(plugin)
        self.append(plugin)

    def add_to_external(self, plugin):
        """
        Add an AigisPlugin to this list, but also to the core list.

        :param AigisPlugin plugin: plugin object to add
        """
        self.external.append(plugin)
        self.append(plugin)

    def bury(self, plugin):
        """
        Move a plugin to the dead list.

        :param AigisPlugin plugin: dead plugin to bury
        """
        if plugin in self:
            self.dead.append(self.pop(self.index(plugin)))

        if plugin in self.core:
            self.core.remove(plugin)

        if plugin in self.external:
            self.external.remove(plugin)
