"""
Responsible for the maintenance and redirecting of all AIGIS's core and plugin features
"""
import atexit
import sys
import toml

from plugins.PluginManager import PluginManager
from plugins.core.Skills import Skills
from diary.LogManager import LogManager
from diary.LogUtils import LOG

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

        # Launch the plugin manager
        LOG.boot("Launching plugin manager...")
        self.plugins = PluginManager()

        # Load core plugins
        LOG.boot("Downloading configured core plugins...")
        self.plugins.load_all(self.config["core"], self.log_manager)
        # Load internal plugins
        LOG.boot("Downloading configured internal plugins...")
        self.plugins.load_all(self.config["internal"], self.log_manager)
        # Load external plugins
        LOG.boot("Downloading configured external plugins...")
        self.plugins.load_all(self.config["external"], self.log_manager)

    def cleanup(self):
        """
        Dribble down the cleanup request to Aigis' components.
        """
        LOG.shutdown("Cleaning up the core...")
        self.plugins.cleanup()
        self.log_manager.cleanup()
