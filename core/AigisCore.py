"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
import atexit
import sys
import toml

from plugins.PluginManager import PluginManager
from plugins.core.Skills import Skills
from diary.LogManager import LogManager
from utils.log_utils import LOG  #pylint: disable=no-name-in-module

_PLUGIN_TYPES = ["core", "internal-local", "internal-remote", "external"]

class Aigis():
    """
    Did I succeed in protecting everyone?

    :param str config: file path to the config to be used for this Aigis instance.
    """
    plugins = None
    config = {}
    log_manager = None
    def __init__(self, config):
        # Register cleanup on exit.
        atexit.register(self.cleanup)

        # Load the config
        LOG.boot("Loading config...")
        self.config = toml.load(config)

        # Launch the logging manager
        LOG.boot("Launching global logging service...")
        self.log_manager = LogManager()

        # Launch the core skill system container
        self.skills = Skills()
        # Expose the core skills object as importable module in order to meme the python syntax
        sys.modules["aigis"] = self.skills

        # Before plugins are even loaded, expose the core skills server
        from proxinator import _aigis
        _aigis.CORE_SERVER.start()

        # Launch the plugin manager
        LOG.boot("Launching plugin manager...")
        self.plugins = PluginManager()

        # Load all plugins in order
        for ptype in _PLUGIN_TYPES:
            LOG.boot("Downloading configured %s plugins...", ptype)
            self.plugins.load_all(self.config[ptype], self.log_manager)
            LOG.boot("All %s plugins loaded!", ptype)

    def cleanup(self):
        """
        Dribble down the cleanup request to Aigis' components.
        """
        LOG.shutdown("Cleaning up the core...")
        self.plugins.cleanup()
        self.log_manager.cleanup()
