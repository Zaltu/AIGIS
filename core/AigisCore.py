"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
from plugins.PluginManager import PluginManager

class Aigis():
    """
    Did I succeed in protecting everyone?

    :param str config: file path to the config to be used for this Aigis instance.
    """
    plugins = PluginManager()
    def __init__(self, config):
        pass





# Aigis needs to
# - load the config
# - prep and start the log service
# - call the plugin loader
# - ???
