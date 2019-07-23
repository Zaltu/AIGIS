"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
import toml

from plugins.PluginManager import PluginManager

class Aigis():
    """
    Did I succeed in protecting everyone?

    :param str config: file path to the config to be used for this Aigis instance.
    """
    plugins = PluginManager()
    config = {}
    def __init__(self, config):
        # Load the config
        self.config = toml.load(config)

        # Launch the logging service






# Aigis needs to
# - prep and start the log service
# - call the plugin loader
# - ???
