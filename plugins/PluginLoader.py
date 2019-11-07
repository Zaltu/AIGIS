"""
Process AIGIS plugin.
"""
import os
import sys
import shutil
import asyncio
import subprocess
import multiprocessing
from threading import Thread
from utils import path_utils, mod_utils, exc_utils  #pylint: disable=no-name-in-module
from plugins.external.WatchDog import jiii
from plugins.internal.WatchDog import jiiii  # 2smug

# Set the dump location for plugin secrets
path_utils.ensure_path_exists(path_utils.SECRET_DUMP)

# Get asyncio event loop for subprocess management
ALOOP = asyncio.get_event_loop()

class Loader():
    """
    Parent class for loading plugins, containing all the logic that is independent to the plugin type.
    """
    @classmethod
    def load(cls, plugin, manager):
        """
        Set up the AIGIS plugin. This means executing the four major steps.
        CONTEXTUALIZE
        REQUIREMENTS
        SECRETS
        RUN

        :param AigisPlugin plugin: the plugin stored in core, regardless of plugin type.
        :param PluginManager manager: this plugin manager singleton

        :raises PluginLoadError: for any problem in loading the plugin
        """
        try:
            cls.contextualize(plugin)
            cls.requirements(plugin)
            cls.copy_secrets(plugin)
            plugin.log.boot("Deploying...")
            cls.run(plugin, manager)
        except exc_utils.PluginLoadError as e:
            plugin.log.error(str(e))
            raise

    @staticmethod
    def contextualize(plugin):
        """
        Apply any plugin contextualization that could be needed to the config,
        depending on numerous factors.
        This is kind of silly, but I'm not sure how to make it better.

        :param AigisPlugin plugin: the plugin stored in core
        """
        plugin.config.ENTRYPOINT = plugin.config.ENTRYPOINT.format(root=plugin.root)
        plugin.config.REQUIREMENT_FILE = plugin.config.REQUIREMENT_FILE.format(root=plugin.root)
        for secret in plugin.config.SECRETS:
            plugin.config.SECRETS[secret] = plugin.config.SECRETS[secret].format(root=plugin.root)

    @staticmethod
    def requirements(plugin):
        """
        Install the requirements for this plugin on the host system, based on the plugin config.

        :param AigisPlugin plugin: the plugin stored in core

        :raises RequirementError: if requirements are not or cannot be met.
        """
        # Check system requirements
        for req in plugin.config.SYSTEM_REQUIREMENTS:
            try:
                assert shutil.which(req)
            except AssertionError:
                raise RequirementError("Fatal error. Host has no %s installed." % req)

        try:
            subprocess.check_call(
                plugin.config.REQUIREMENT_COMMAND.split(" ") + [plugin.config.REQUIREMENT_FILE],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            raise RequirementError("Requirement install exited with error code %s" % str(e))
        except Exception as e:
            raise RequirementError(
                "Could not process requirements %s. The following error occured:\n%s" %
                (plugin.config.REQUIREMENT_FILE, str(e))
            )

        plugin.log.boot("Requirements processed successfully...")

    @staticmethod
    def copy_secrets(plugin):
        """
        Copy any potential secrets a plugin could have from the AIGIS secret dump to the specified location.
        Will not copy anything is a file is missing.

        :param AigisPlugin plugin: plugin registered in core

        :raises MissingSecretFileError: if a specified secret cannot be found.
        """
        missing_secrets = []
        for secret in plugin.config.SECRETS:
            if not os.path.exists(os.path.join(path_utils.SECRET_DUMP, os.path.join(plugin.name, secret))):
                missing_secrets.append(os.path.join(
                    path_utils.SECRET_DUMP,
                    os.path.join(plugin.name, secret)
                ))
        if not missing_secrets:
            for secret in plugin.config.SECRETS:
                path_utils.ensure_path_exists(plugin.config.SECRETS[secret])
                shutil.copy2(
                    os.path.join(
                        path_utils.SECRET_DUMP,
                        os.path.join(plugin.name, secret)
                    ),
                    plugin.config.SECRETS[secret]
                )
        else:
            raise MissingSecretFileError(
                "The following secret files are missing:\n" + "\n".join(missing_secrets)
            )

    @staticmethod
    def run(plugin, manager):
        """
        This function launches the plugin following different logic depending on the plugin type
        specified in the config.

        :param AigisPlugin plugin: plugin to be passed to the WatchDog for external processes
        :param PluginManager manager: this instance's PluginManager to be passed to WatchDogs
        for external processes

        :raises InvalidPluginTypeError: if the plugin type specified in the plugin config is not valid
        """
        raise InvalidPluginTypeError("Cannot process plugin type %s." % plugin.config.PLUGIN_TYPE)

    @staticmethod
    def reload(plugin, manager):
        """
        This plugin exposes an aigis.<module>.AIGISreload function in the aigis core module for each plugin.
        This allows plugins to be reloaded (and potentially updated) without needing to have the "restart"
        option selected. Since it's difficult/impossible to crash core plugins as well, this is done from
        here.

        :param AigisPlugin plugin: the plugin to reload
        :param PluginManager manager: the plugin manager singleton

        :raises InvalidPluginTypeError: if the plugin type specified in the plugin config is not valid
        """
        raise InvalidPluginTypeError(
            "Cannot reload plugin %s. Plugin type invalid. How was it loaded to begin with?" % plugin.name
        )


class LoadCore(Loader):
    """
    Plugin loader for the CORE plugin type.
    """
    @staticmethod
    def run(plugin, manager):
        """
        Core implementation of run.
        Parses the environment of the core injection file provided by the plugin and integrates the exposed
        functionality into the AIGIS Skills core. Functionality is wrapped with an AIGIS log object if the
        plugin functions accept it.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton
        """
        import aigis as core_skills # AigisCore.skills
        # We need to add the plugin config's entrypoint to the PYTHONPATH
        # so imports work as expected on requirements
        sys.path.append(plugin.config.ENTRYPOINT)
        core_skills._AIGISlearnskill(
            mod_utils.import_from_path(
                _prep_core_injector_file(plugin)
            ),
            plugin
        )
        plugin.log.boot("Skills acquired.")

    @staticmethod
    def reload(plugin, manager):
        """
        Fully kill the core plugin by removing all it's references in the core skills object then request
        the manager to reload it.
        WARNING that this won't update the available libraries in internal or external plugins unless they
        too are reloaded, since the references are sourced on launch.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton
        """
        import aigis as core_skills # AigisCore.skills
        # We need to add the plugin config's entrypoint to the PYTHONPATH
        # so imports work as expected on requirements
        core_skills._AIGISforgetskill(
            mod_utils.import_from_path(
                _prep_core_injector_file(plugin)
            ),
            plugin
        )
        plugin.log.boot("Skills deregistered.")
        plugin.reload = True
        manager.bury(plugin)


class LoadInternalLocal(Loader):
    """
    Plugin loader for the INTERNAL-LOCAL plugin type.
    """
    @staticmethod
    def contextualize(plugin):
        """
        Plugin-type specific contextualizer. On top of the usual, internal-local plugins also format the
        LAUNCH option with {root}.

        :param AigisPlugin plugin: the plugin
        """
        Loader.contextualize(plugin)
        # launch is only a path on internal plugins
        plugin.config.LAUNCH = plugin.config.LAUNCH.format(root=plugin.root)

    @staticmethod
    def run(plugin, manager):
        """
        Internal-local implementation of run.
        Spawns a subprocess and instanciates that python environment to include the core_skills singleton to
        expose all the core functionality in the subprocess. Also maintains a watchdog thread that monitors
        for the process to exit. The stdout/err of the subprocess is NOT captured, but an AIGIS logging
        object is passed to the subprocess environment for use.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton
        """
        import aigis as core_skills # AigisCore.skills
        # We need to add the plugin config's entrypoint to the PYTHONPATH
        # so imports work as expected on requirements
        sys.path.append(plugin.config.ENTRYPOINT)
        core_file = _prep_core_injector_file(plugin)
        if core_file:
            core_skills._AIGISlearnskill(
                mod_utils.import_from_path(core_file),
                plugin.log
            )
            plugin.log.boot("Internal plugin registered skills...")
        plugin._int_proc = multiprocessing.Process(
            target=LoadInternalLocal._wrap_child_process_launch,
            args=(plugin.config.LAUNCH, core_skills, plugin.log)
        )
        plugin._int_proc.start()
        Thread(target=LoadInternalLocal._threaded_child_process_wait, args=(plugin, manager)).start()

    @staticmethod
    def reload(plugin, manager):
        """
        Reload an internal plugin by setting it's reload flag and killing the process.
        Realistically, this may not be safe for all plugins. Up to user to use responsibly.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton

        :raises AttributeError: if the plugin has no internal process attached to it
        """
        plugin.reload = True
        try:
            plugin._int_proc.kill()
        except AttributeError as e:
            raise AttributeError("Missing internal process for plugin %s. A reload request was made when the"
                                 "plugin wasn't active.") from e


    @staticmethod
    def _wrap_child_process_launch(fpath, aigis, log):
        """
        Get a function wrapping the functionality needed to launch an internal plugin with the correct
        AIGIS runtime context. Sets the aigis instance as an importable module and calls the start
        function with the logger.

        NEVER CALL THIS DIRECTLY IN THE MAIN PROCESS.

        :param str fpath: path to launch file
        :param object aigis: the aigis core module
        :param logging.logger log: the plugin's AigisLog's logger

        :raises AttributeError: amongst other things when no "launch" function can be found in the specified
        launch file.
        """
        # This should be run in a separate process
        sys.modules["aigis"] = aigis
        try:
            launch_mod = mod_utils.import_from_path(fpath)
            launch_mod.launch(log)
        except AttributeError:
            log.error("Cannot find the required function \"launch\" in the file %s", fpath)
            raise

    @staticmethod
    def _threaded_child_process_wait(plugin, manager):
        jiiii(plugin, manager)


class LoadExternal(Loader):
    """
    Plugin loader for the EXTERNAL plugin type.
    """
    @staticmethod
    def run(plugin, manager):
        """
        External plugin implementation of run.
        Spawns a new process using the plugin's configuration to launch the external application as an
        independent program. It does however maintain a watchdog thread that watches for that process to
        exit and captures the stdout/err pipes for logging.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton
        """
        ALOOP.run_until_complete(LoadExternal._run_external(plugin))
        plugin.log.boot("Running...")
        Thread(target=LoadExternal._threaded_async_process_wait, args=(plugin, manager)).start()

    @staticmethod
    def reload(plugin, manager):
        """
        Reload an external plugin by setting it's reload flag and killing the process.
        Realistically, this may not be safe for all plugins. Up to user to use responsibly.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton

        :raises AttributeError: if the plugin has no external process attached to it
        """
        plugin.reload = True
        try:
            plugin._ext_proc.kill()
        except AttributeError as e:
            raise AttributeError("Missing external process for plugin %s. A reload request was made when the"
                                 "plugin wasn't active.") from e

    @staticmethod
    async def _run_external(plugin):
        """
        Launch an asyncio subprocess.

        :param AigisPlugin plugin: the plugin
        """
        plugin._ext_proc = await asyncio.create_subprocess_exec(*plugin.config.LAUNCH,
                                                                cwd=plugin.config.ENTRYPOINT)

    @staticmethod
    def _threaded_async_process_wait(plugin, manager):
        """
        Launch the Watchdog for this plugin's process.
        Can only be called on an external plugin.

        :param AigisPlugin plugin: the external plugin to wait for.
        :param PluginManager manager: this instance's PluginManager
        """
        ALOOP.run_until_complete(jiii(plugin, manager))


def _prep_core_injector_file(plugin):
    """
    Fetch the path to the core injection file of a core plugin.
    We need to append the core plugin's ENTRYPOINT to the PYTHONPATH so that the core injection
    file can process relative imports independantly of where the plugin is locally loaded. Without
    this step, imports in those files would have to include "ext.<plugin_name>." in front of every
    import...

    :param AigisPlugin plugin: the core plugin to load

    :returns: the local path to the core plugin injector file
    :rtype: str

    :raises InvalidPluginTypeError: if no injector file can be found, the plugin must be misconfigured.
    """
    core_file = os.path.join(plugin.root, "AIGIS/AIGIS.core")
    if not os.path.exists(core_file):
        if plugin.type == "core":
            raise InvalidPluginTypeError(
                "No AIGIS/AIGIS.core file found. Plugin is not configured as a core plugin..."
            )
        return None
    return core_file


class RequirementError(exc_utils.PluginLoadError):
    """
    Error for issues in handling plugin requirements.
    """


class MissingSecretFileError(exc_utils.PluginLoadError):
    """
    Error to be thrown when a specified secrets file cannot be found.
    """


class InvalidPluginTypeError(exc_utils.PluginLoadError):
    """
    Error when plugin config has an unsupported type or is not configured for it's type.
    """
