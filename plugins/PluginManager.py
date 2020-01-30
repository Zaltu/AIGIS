"""
Helper module to hold and organize loaded plugins.
"""
import os
import shutil
import traceback
import subprocess

import pygit2

from utils import path_utils, exc_utils  #pylint: disable=no-name-in-module
from plugins.AigisPlugin import AigisPlugin
from diary.AigisLog import LOG

class PluginManager(list):
    """
    Helper class to hold and organize loaded plugins.
    """
    dead = []
    def __init__(self):
        super().__init__(self)
        path_utils.ensure_path_exists(path_utils.PLUGIN_ROOT_PATH)

    def load_all(self, config, log_manager):
        """
        Download the plugins specified in the config

        :param dict config: the loaded plugins section of the config
        :param LogManager log_manager: the log manager for this AIGIS instance
        """
        for plugin_name in config:
            LOG.info("Loading plugin %s...", plugin_name)
            try:
                self._load_one(plugin_name, log_manager, config[plugin_name])
            except Exception as e:  #pylint: disable=broad-except
                LOG.error("Could not load plugin %s!\n%s", plugin_name, str(e))

    def bury(self, plugin):
        """
        Move a plugin to the dead list.

        :param AigisPlugin plugin: dead plugin to bury
        """
        if plugin.restart or plugin.reload:
            if plugin.reload:
                plugin.log.info("Attempting to reload plugin...")
                plugin.reload = False
            elif plugin.restart:
                plugin.log.info("Attempting to restart plugin...")
                plugin.restart -= 1

            self._try_load(plugin)
            return

        if plugin in self:
            safe_cleanup(plugin)
            self.dead.append(self.pop(self.index(plugin)))
            plugin.log.shutdown("Plugin shut down.")
            LOG.warning("%s has terminated.", plugin.name)
        else:
            LOG.warning("Plugin %s in an unexpected state, but not blocking.", plugin.name)

    def cleanup(self):
        """
        Request all plugins clean themselves up.
        """
        LOG.shutdown("Requesting plugins clean themselves up.")
        for plugin in self:
            safe_cleanup(plugin)

    def _load_one(self, plugin_name, log_manager, plugin_url):
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
        :param LogManager log_manager: the AIGIS LogManager singleton for this execution
        :param str plugin_url: web URL from which to download the plugin
        """
        plugin = AigisPlugin(plugin_name, log_manager)

        plugin.log.boot("Downloading plugin...")
        if not download_plugin(plugin, plugin_url, plugin.root):
            return

        plugin.configure()

        plugin.log.boot("Preparing to launch...")
        self._try_load(plugin)

    def _try_load(self, plugin):
        """
        Attempt to safely launch a single given plugin using it's launcher. Catch errors and respond
        appropriately. This is a private function to PluginManager since it bypasses the `bury` function and
        ends the plugin's cycle immediately if unsucessful.

        :param AigisPlugin plugin: the plugin to load

        :raises Exception: numerous exception types can be bubbled up from the various loading mechanisms
        """
        try:
            plugin.loader.load(plugin, self)
            self.append(plugin)
        except Exception as e:
            if isinstance(e, exc_utils.PluginLoadError):
                plugin.log.shutdown("Could not load plugin, shutting down...")
            else:
                plugin.log.shutdown("Unknown error occurred launching plugin:\n%s", traceback.format_exc())
            self.pop(self.index(plugin))
            self.dead.append(plugin)
            safe_cleanup(plugin)
            raise


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


def safe_cleanup(plugin):
    """
    Clean up a plugin in a safe way by catching errors.
    Still log those errors as they are though. This is just so AIGIS doesn't crash, since that would be very
    bad.

    :param AigisPlugin plugin: plugin to clean up
    """
    # Make sure the plugin doesn't accitendally try and restart
    plugin.restart = 0
    plugin.reload = False

    # Try and run the plugin's cleanup function. Skipped if error.
    try:
        plugin.cleanup()
    except:  #pylint: disable=bare-except
        LOG.ERROR("PROBLEM CLEANING UP %s, CLEANUP SKIPPED! CHECK YOUR RESOURCES.", plugin.name)

    plugin.loader.stop(plugin)
