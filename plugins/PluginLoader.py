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

def load(plugin, manager):
    """
    Set up the AIGIS plugin. This means executing the four major steps.
    CONTEXTUALIZE
    REQUIREMENTS
    SECRETS
    RUN

    :param AigisPlugin plugin: the plugin stored in core, regardless of plugin type.
    :param PluginManager manager: this instance's PluginManager

    :raises PluginLoadError: for any problem in loading the plugin
    """
    try:
        contextualize(plugin)
        requirements(plugin)
        copy_secrets(plugin)
        plugin.log.boot("Deploying...")
        run(plugin, manager)
    except exc_utils.PluginLoadError as e:
        plugin.log.error(str(e))
        raise


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
    if "internal" in plugin.type:  # launch is only a path on internal plugins
        plugin.config.LAUNCH = plugin.config.LAUNCH.format(root=plugin.root)


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
            missing_secrets.append(os.path.join(path_utils.SECRET_DUMP, os.path.join(plugin.name, secret)))
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
        raise MissingSecretFileError("The following secret files are missing:\n" + "\n".join(missing_secrets))


def run(plugin, manager):
    """
    This function launches the plugin following different logic depending on the plugin type
    specified in the config.

    :param AigisPlugin plugin: plugin to be passed to the WatchDog for external processes
    :param PluginManager manager: this instance's PluginManager to be passed to the WatchDog
    for external processes

    :raises InvalidPluginTypeError: if the plugin type specified in the plugin config is not valid
    """
    if plugin.config.PLUGIN_TYPE == "external":
        ALOOP.run_until_complete(_run_external(plugin))
        plugin.log.boot("Running...")
        Thread(target=_threaded_async_process_wait, args=(plugin, manager)).start()
    elif plugin.config.PLUGIN_TYPE == "core":
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
    elif plugin.config.PLUGIN_TYPE == "internal-local":
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
            target=_wrap_child_process_launch,
            args=(plugin.config.LAUNCH, core_skills, plugin.log)
        )
        plugin._int_proc.start()
        Thread(target=_threaded_child_process_wait, args=(plugin, manager)).start()
    else:
        raise InvalidPluginTypeError("Cannot process plugin type %s." % plugin.config.PLUGIN_TYPE)


async def _run_external(plugin):
    """
    Launch an asyncio subprocess.

    :param AigisPlugin plugin: the plugin
    """
    plugin._ext_proc = await asyncio.create_subprocess_exec(*plugin.config.LAUNCH,
                                                            cwd=plugin.config.ENTRYPOINT)


def _threaded_async_process_wait(plugin, manager):
    """
    Launch the Watchdog for this plugin's process.
    Can only be called on an external plugin.

    :param AigisPlugin plugin: the external plugin to wait for.
    :param PluginManager manager: this instance's PluginManager
    """
    ALOOP.run_until_complete(jiii(plugin, manager))


def _threaded_child_process_wait(plugin, manager):
    jiiii(plugin, manager)


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
