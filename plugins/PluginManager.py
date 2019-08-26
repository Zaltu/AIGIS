"""
Helper module to hold and organize loaded plugins.
"""
import os
import importlib.util
import subprocess
import traceback

import pygit2

from utils.path_utils import ensure_path_exists  #pylint: disable=no-name-in-module
from plugins.AigisPlugin import AigisPlugin
from plugins import PluginLoader
from diary.AigisLog import LOG

PLUGIN_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ext"))

class PluginManager(list):
    """
    Helper class to hold and organize loaded plugins.
    """
    core = []
    external = []
    dead = []
    def __init__(self):
        super().__init__(self)
        ensure_path_exists(PLUGIN_ROOT_PATH)

    def load_all(self, config, log_manager):
        """
        Download the plugins specified in the config

        :param dict config: the loaded plugins section of the config
        :param LogManager log_manager: the log manager for this AIGIS instance
        """
        LOG.boot("Downloading configured plugins...")
        for plugin in config:
            plugin_path = os.path.join(PLUGIN_ROOT_PATH, plugin)
            plugin_config_path = os.path.join(plugin_path, "AigisBot/config.py")

            LOG.boot("Downloading plugin %s...", plugin)
            if not download_plugin(plugin, config[plugin], plugin_path):
                continue

            LOG.boot("Getting %s config...", plugin)
            plugin_config = _plugin_config_generator(plugin, plugin_config_path)
            if not plugin_config:
                continue

            LOG.boot("Prepping and launching %s", plugin)
            try:
                self.append(self._aigisplugin_load_wrapper(plugin, plugin_path, plugin_config, log_manager))
            except:  #pylint: disable=bare-except
                LOG.error("Could not load plugin %s!\n%s", plugin, traceback.format_exc(limit=3))

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
            plugin.cleanup()

            if plugin in self.core:
                self.core.remove(plugin)

            if plugin in self.external:
                self.external.remove(plugin)

        plugin.log.SHUTDOWN("Plugin buried.")
        LOG.warning("%s has terminated.", plugin.name)

    def cleanup(self):
        """
        Request all plugins clean themselves up.
        """
        LOG.shutdown("Requesting plugins clean themselves up.")
        for plugin in self:
            plugin.cleanup()

    def _aigisplugin_load_wrapper(self, plugin_name, plugin_path, plugin_config, log_manager):
        """
        Wrapper around AigisPlugin instantiation to avoid python object reference issues.

        :param str plugin_name: plugin name
        :param str plugin_path: path to plugin
        :param str plugin_config: plugin config module
        :param LogManager log_manager: the log manager for this AIGIS instance

        :returns: plugin object
        :rtype: AigisPlugin

        :raises RequirementError: if there is an Exception while processing the plugin's requirements.
        """
        plugin = AigisPlugin(plugin_name, plugin_path, plugin_config.PLUGIN_TYPE, log_manager)
        try:
            PluginLoader.load(plugin_config, plugin, self)
        except PluginLoader.RequirementError:
            self.dead.append(plugin)
            raise
        return plugin



def download_plugin(plugin_name, github_path, plugin_path):
    """
    Download a plugin to a local path

    :param str plugin_name: name of plugin to download
    :param str github_path: path to download
    :param str plugin_path: path to download to

    :returns: if instruction was successful
    :rtype: bool
    """
    if ensure_path_exists(os.path.join(PLUGIN_ROOT_PATH, plugin_name)):
        try:
            LOG.info("%s already installed, making sure it's up to date...", plugin_name)
            subprocess.check_output(["git", "pull"], cwd=plugin_path)
        except Exception:  #pylint: disable=broad-except
            LOG.warning("Unable to update plugin %s. Git Pull failed.", plugin_name)
        return True
    try:
        _download(github_path, plugin_path)
    except IOError:
        LOG.error("Problem accessing filepath, skipping plugin %s", plugin_name)
        return False
    return True


def _download(url, plugin_path):
    """
    Download a specific plugin

    :param str url: the github url to download ("account/repo-name")
    :param str plugin_path: path to download to
    """
    pygit2.clone_repository(url, plugin_path, checkout_branch="new-aigis-setup")


def _plugin_config_generator(plugin_name, config_path):
    """
    Generate a new plugin config object

    :param str plugin_name: plugin name
    :param str config_path: path to plugin config file

    :returns: config module or None
    :rtype: Module
    """
    spec = importlib.util.spec_from_file_location("config", config_path)
    plugin_config = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(plugin_config)
    except FileNotFoundError:
        LOG.error("Plugin %s has no AigisBot configuration file at %s", plugin_name, config_path)
        return None
    return plugin_config
