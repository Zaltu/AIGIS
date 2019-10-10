"""
Helper module to hold and organize loaded plugins.
"""
import os
import subprocess
import shutil
import traceback

import pygit2

from utils import path_utils, mod_utils, exc_utils  #pylint: disable=no-name-in-module
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
        path_utils.ensure_path_exists(PLUGIN_ROOT_PATH)

    def load_all(self, config, log_manager):
        """
        Download the plugins specified in the config

        :param dict config: the loaded plugins section of the config
        :param LogManager log_manager: the log manager for this AIGIS instance
        """
        for plugin_name in config:
            LOG.info("Loading plugin %s...", plugin_name)
            plugin_path = os.path.join(PLUGIN_ROOT_PATH, plugin_name)
            plugin_config_path = os.path.join(plugin_path, "AIGIS/AIGIS.config")
            try:
                self._load_one(plugin_name, plugin_path, plugin_config_path, log_manager, config[plugin_name])
            except Exception as e:  #pylint: disable=broad-except
                LOG.error("Could not load plugin %s!\n%s", plugin_name, str(e))

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

        plugin.log.shutdown("Plugin shut down.")
        LOG.warning("%s has terminated.", plugin.name)

    def cleanup(self):
        """
        Request all plugins clean themselves up.
        """
        LOG.shutdown("Requesting plugins clean themselves up.")
        for plugin in self:
            plugin.cleanup()

    def _load_one(self, plugin_name, plugin_path, plugin_config_path, log_manager, plugin_url):
        """
        Fully load one plugin. This includes
        - generating the AigisPlugin object (with logger)
        - downloading the plugin source if necessary, or
        - updating it if it already exists
        - loading the plugin config as a module and
        - attempting to load the plugin via PluginLoader
        This function handles only logging error and issues to the plugin-specific loggers.
        In any case of error loading the plugin, an exception will be raised.

        :param str plugin_name: name of plugin to load
        :param str plugin_path: local path the plugin should reside in
        :param str plugin_config_path: path to the local AIGIS-compatible config file for this plugin
        :param LogManager log_manager: the AIGIS LogManager singleton for this execution
        :param str plugin_url: web URL from which to download the plugin

        :raises FileNotFoundError: explicitely if the config file cannot be found locally once the plugin
        has been downloaded
        :raises Exeption: numerous exception types can be bubbled up from the various loading mechanisms
        """
        plugin = AigisPlugin(plugin_name, plugin_path, log_manager)

        plugin.log.boot("Downloading plugin...")
        if not download_plugin(plugin, plugin_url, plugin_path):
            return

        plugin.log.boot("Getting config...")
        try:
            plugin_config = mod_utils.import_from_path(plugin_config_path)
        except FileNotFoundError as e:
            plugin.log.error(str(e))
            plugin.log.shutdown("Could not get configuration for plugin %s!", plugin.name)
            raise

        # VERY IMPORTANT
        plugin.type = plugin_config.PLUGIN_TYPE

        plugin.log.boot("Preparing to launch...")
        self.append(self._aigisplugin_load_wrapper(plugin, plugin_config))


    def _aigisplugin_load_wrapper(self, plugin, plugin_config):
        """
        Specifically load the plugin.

        :param AigisPlugin plugin: the plugin object
        :param str plugin_config: plugin config module

        :returns: plugin object
        :rtype: AigisPlugin

        :raises PluginLoadError: for any error occurring while trying to launch the plugin
        :raises Exception: for any other system errors preventing the plugin from being launched.
        """
        try:
            PluginLoader.load(plugin_config, plugin, self)
        except exc_utils.PluginLoadError:
            plugin.log.shutdown("Could not load plugin, shutting down...")
            self.dead.append(plugin)
            plugin.cleanup()
            raise
        except Exception:
            plugin.log.shutdown("Unknown error occurred launching plugin:\n%s", traceback.format_exc())
            raise
        return plugin


def download_plugin(plugin, source_path, plugin_path):
    """
    Put plugin in runtime location by either copying it from a location on disk or cloning it from github.

    :param AigisPlugin plugin: the plugin object
    :param str source_path: either the path on disk to the plugin source or the github https clone link
    :param str plugin_path: the path to put the plugin for this runtime

    :returns: if download was successful
    :rtype: bool
    """
    if os.path.exists(source_path):
        return _local_copy_plugin(plugin, source_path, plugin_path)
    return _git_download_plugin(plugin, source_path, plugin_path)


def _local_copy_plugin(plugin, local_source, plugin_path):
    """
    Copy a plugin's source from a location on disk to the runtime plugin path.

    :param AigisPlugin plugin: plugin object
    :param str local_source: path to copy from
    :param str plugin_path: path to copy to

    :returns: if instruction was successful
    :rtype: bool
    """
    if os.path.exists(plugin_path):
        plugin.log.warning("Plugin exists, it will not get updated.")
        return True
    try:
        shutil.copytree(local_source, plugin_path)
    except Exception as e:  #pylint: disable=broad-except
        plugin.log.error(
            "Could not copy files from\n%s to\n%s because\n%s", local_source, plugin_path, str(e)
        )
        return False
    return True


def _git_download_plugin(plugin, github_path, plugin_path):
    """
    Download a plugin from github to a local path

    :param AigisPlugin plugin: plugin object
    :param str github_path: path to download
    :param str plugin_path: path to download to

    :returns: if instruction was successful
    :rtype: bool
    """
    if path_utils.ensure_path_exists(plugin_path):
        try:
            plugin.log.info("Plugin already installed, making sure it's up to date...")
            subprocess.check_output(["git", "pull"], cwd=plugin_path)
        except Exception:  #pylint: disable=broad-except
            plugin.log.warning("Unable to update plugin. Git Pull failed.")
        return True
    try:
        _download(github_path, plugin_path)
    except IOError:
        plugin.log.error("Problem accessing filepath, skipping plugin")
        return False
    return True


def _download(url, plugin_path):
    """
    Download a specific plugin

    :param str url: the github url to download ("account/repo-name")
    :param str plugin_path: path to download to
    """
    pygit2.clone_repository(url, plugin_path, checkout_branch="master")
