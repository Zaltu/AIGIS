"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
import toml

from plugins.PluginManager import PluginManager
from utils.AigisLog import LogManager, LOG  #pylint: disable=no-name-in-module

class Aigis():
    """
    Did I succeed in protecting everyone?

    :param str config: file path to the config to be used for this Aigis instance.
    """
    plugins = None
    config = {}
    log_manager = None
    def __init__(self, config):
        # Load the config
        LOG.info("Loading config...")
        self.config = toml.load(config)

        # Launch the logging manager
        LOG.info("Launching global logging service...")
        self.log_manager = LogManager()

        # Launch the plugin manager
        LOG.info("Launching plugin manager")
        self.plugins = PluginManager()







# Aigis needs to
# - prep and start the log service
# - call the plugin loader
# - ???
