"""
Representation of a plugin with handlers used by the core to properly route traffic.
"""
import os

from utils import mod_utils, path_utils  #pylint: disable=no-name-in-module
from plugins import PluginLoader

_LOADER_TYPES = {
    "core": PluginLoader.LoadCore,
    "internal": PluginLoader.LoadInternalLocal,
    "internal-remote": PluginLoader.LoadInternalLocal,
    "external": PluginLoader.LoadExternal,
    "default": PluginLoader.Loader  # Planned error
}

class AigisPlugin():
    """
    A plugin that can be managed by AIGIS and it's core.

    :param str name: name of the plugin
    :param LogManager log_manager: the log manager for this AIGIS instance
    :param str ptype: the plugin type
    :param bool restart: whether an auto-restart should be attempted on death
    :param object config: the plugin's config namespace
    :param PluginLoader.Loader loader: loader class appropriate for this plugin
    """
    def __init__(self, name, log_manager, ptype=None, restart=0, config=None, loader=None):
        self.id = id(self)
        self.name = name
        self.root = os.path.join(path_utils.PLUGIN_ROOT_PATH, self.name)
        self.config_path = os.path.join(self.root, "AIGIS/AIGIS.config")
        self.type = ptype
        self.restart = restart
        self.reload = False
        self.config = config
        self.loader = loader
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

    def configure(self):
        """
        Load the configuration object and configure the plugin accordingly. This step is essential and
        plugins should never be launched without first being configured. It will crash.

        :raises FileNotFoundError: if the config file cannot be found
        """
        self.log.boot("Getting config...")
        try:
            self.config = mod_utils.import_from_path(self.config_path)
        except FileNotFoundError as e:
            self.log.error(str(e))
            self.log.shutdown("Could not get configuration for plugin %s!", self.name)
            raise

        # VERY IMPORTANT
        self.type = self.config.PLUGIN_TYPE
        self.restart = getattr(self.config, "RESTART", 0)
        if not hasattr(self.config, "SECRETS"):
            setattr(self.config, "SECRETS", {})
        if self.type == "internal" and hasattr(self.config, "HOST"):
            self.type = "internal-remote"
        self.loader = _LOADER_TYPES.get(self.type, _LOADER_TYPES.get("default"))

    def cleanup(self):
        """
        Container function to handle cleaning up any resources used by the plugin.
        By default does nothing. Should be overwritten if cleanup is required.
        """
