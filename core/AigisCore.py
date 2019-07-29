"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
import atexit
import toml

from plugins.PluginManager import PluginManager
from utils.LogManager import LogManager  #pylint: disable=no-name-in-module
from utils.LogUtils import LOG  #pylint: disable=no-name-in-module

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

        # Launch the plugin manager
        LOG.boot("Launching plugin manager")
        self.plugins = PluginManager()

    def cleanup(self):
        """
        Dribble down the cleanup request to Aigis' components.
        """
        LOG.shutdown("Cleaning up the core...")
        self.plugins.cleanup()
        self.log_manager.cleanup()


# Aigis needs to
# - call the plugin loader
# - ???
