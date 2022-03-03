"""
Process AIGIS plugin.
"""
#pylint: disable=import-error
import os
import sys
import time
import shutil
import asyncio
import subprocess
from threading import Thread
from utils import path_utils, mod_utils, exc_utils
from plugins.external.WatchDog import jiii


# Set the dump location for plugin secrets
path_utils.ensure_path_exists(path_utils.SECRET_DUMP)

# Setup the asyncio event loop for subprocess management
ALOOP = asyncio.new_event_loop()
ALOOP_FOREVER = Thread(target=ALOOP.run_forever, daemon=True)
ALOOP_FOREVER.start()

# Max number of seconds to launch a plugin.
PLUGIN_LAUNCH_TIMEOUT = 10

class PluginIO():
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
        #if hasattr(plugin.config, "REQUIREMENT_FILE"):  # Requirements are not mandatory
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
        except AttributeError:
            plugin.log.warning("No requirements provided, attempting to start plugin regardless.")
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
        This plugin exposes an aigis.AIGISreload function in the aigis core module.
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

    @staticmethod
    def stop(plugin, manager):
        """
        Stop the plugin in as non-violent a way as possible.
        Does not handle what kind of retry, if any, is attempted on burial.

        :param AigisPlugin plugin: the plugin to stop
        :param PluginManager manager: the plugin manager, for burial if needed
        """

class CoreIO(PluginIO):
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

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton
        """
        plugin.reload = True
        CoreIO.stop(plugin, manager)

    @staticmethod
    def stop(plugin, manager):
        """
        Unregister the skills of the core plugin and tell the manager to bury it.

        :param AigisPlugin plugin: plugin to stop
        :param PluginManager manager: manager singleton for burial
        """
        import aigis as core_skills # AigisCore.skills
        core_skills._AIGISforgetskill(
            mod_utils.import_from_path(
                _prep_core_injector_file(plugin)
            ),
            plugin
        )
        plugin.log.shutdown("Skills deregistered.")
        manager.bury(plugin)


class InternalLocalIO(PluginIO):
    """
    Plugin loader for the INTERNAL-LOCAL plugin type.
    """
    ProxyPath = os.path.abspath(os.path.join(os.path.dirname(__file__), "../proxinator/injector/aigis.py"))
    @staticmethod
    def contextualize(plugin):
        """
        Plugin-type specific contextualizer. On top of the usual, internal-local plugins also format the
        LAUNCH option with {root}.

        :param AigisPlugin plugin: the plugin
        """
        PluginIO.contextualize(plugin)
        # launch is only a path on internal plugins
        plugin.config.LAUNCH = plugin.config.LAUNCH.format(root=plugin.root)

    @staticmethod
    def run(plugin, manager):
        """
        Internal-local implementation of run.
        Spawns a subprocess and instanciates that python environment to include the core_skills singleton to
        expose all the core functionality in the subprocess. Also maintains a watchdog thread that monitors
        for the process to exit. The stdout/err of the subprocess is captured and piped to the plugin's log's
        filehandler.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton

        :raises PluginLaunchTimeoutError: if plugin fails to launch within the timeout value
        """
        core_file = _prep_core_injector_file(plugin)
        if core_file:
            # We need to add the plugin config's entrypoint to the PYTHONPATH
            # so imports work as expected on requirements
            sys.path.append(plugin.config.ENTRYPOINT)
            import aigis
            aigis._AIGISlearnskill(
                mod_utils.import_from_path(core_file),
                plugin
            )
            plugin.log.boot("Internal plugin registered skills...")

        try:
            asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(InternalLocalIO._run_internal(plugin, manager, False), ALOOP)
        except RuntimeError:  # No running event loop (first boot)
            fut = asyncio.run_coroutine_threadsafe(InternalLocalIO._run_internal(plugin, manager, True), ALOOP)
            fut.result()  # Block
            asyncio.run_coroutine_threadsafe(jiii(plugin, manager), ALOOP)


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
        InternalLocalIO.stop(plugin)

    @staticmethod
    async def _run_internal(plugin, manager, isfirst):
        """
        Launch an asyncio subprocess.

        :param AigisPlugin plugin: the plugin
        """
        plugin._ext_proc = await asyncio.create_subprocess_exec(
            *[
                sys.executable,
                InternalLocalIO.ProxyPath,
                "--ENTRYPOINT", plugin.config.ENTRYPOINT,
                "--LAUNCH", plugin.config.LAUNCH
            ],
            stdout=plugin.log.filehandler,
            stderr=plugin.log.filehandler
        )
        plugin.log.boot("Running...")
        if not isfirst:
            asyncio.run_coroutine_threadsafe(jiii(plugin, manager), ALOOP)


    @staticmethod
    def stop(plugin, manager=None):
        """
        Stop the plugin in as non-violent a way as possible.
        Killing the plugin will automatically cause the manager to bury it, so no need to do so manually.

        :param AigisPlugin plugin: the plugin to stop
        :param PluginManager manager: unused, but required by parent
        """
        _stop(plugin)


class InternalRemoteIO(PluginIO):
    """
    Launch an internal plugin on a remote host
    """
    # TODO


class ExternalIO(PluginIO):
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
        ALOOP.run_until_complete(ExternalIO._run_external(plugin))  # TODO busted
        plugin.log.boot("Running...")
        Thread(target=_threaded_async_process_wait, args=(plugin, manager, ALOOP), daemon=True).start()

    @staticmethod
    def reload(plugin, manager):
        """
        Reload an external plugin by setting it's reload flag and killing the process.
        Realistically, this may not be safe for all plugins. Up to user to use responsibly.

        :param AigisPlugin plugin: the plugin
        :param PluginManager manager: the plugin manager singleton

        :raises AttributeError: if the plugin has no external process attached to it
        """
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
    def stop(plugin, manager=None):
        """
        Stop the plugin in as non-violent a way as possible.
        Killing the plugin will automatically cause the manager to bury it, so no need to do so manually.

        :param AigisPlugin plugin: the plugin to stop
        :param PluginManager manager: unused, but required by parent
        """
        _stop(plugin)


def _stop(plugin):
    """
    Stop the plugin in as non-violent a way as possible.
    Send a SIGTERM and wait for 5 seconds. If process is still running, send SIGKILL.

    :param AigisPlugin plugin: the plugin to stop
    """
    try:
        plugin._ext_proc.terminate()
    except ProcessLookupError:
        # Process already dead. Probably exited earlier.
        return

    # This chunk is necessary because Python async FUCKING SUCKS
    # Keep checking for return code on process. We can't wait for it because it wouldn't block the process
    # and then the task may not finish.
    start = time.time()
    while plugin._ext_proc.returncode is None and time.time()-start < 5:
        time.sleep(0.01)

    if plugin._ext_proc.returncode is None:
        plugin.log.warning("Plugin taking too long to terminate, killing it.")
        plugin._ext_proc.kill()


def _threaded_async_process_wait(plugin, manager):
    """
    Launch the Watchdog for this plugin's process.
    Can only be called on an external plugin.

    :param AigisPlugin plugin: the external plugin to wait for.
    :param PluginManager manager: this instance's PluginManager
    :param AbstractEventLoop loop: the tmp generated event loop to run the watcher in
    """
    asyncio.run_coroutine_threadsafe(jiii(plugin, manager), loop=ALOOP)


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

class PluginLaunchTimeoutError(exc_utils.PluginLoadError):
    """
    Error for when the plugin is taking too long to launch.
    """
