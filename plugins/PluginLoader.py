"""
Process AIGIS plugin.
"""
import os
import shutil
import asyncio
from utils.path_utils import ensure_path_exists  #pylint: disable=no-name-in-module
from plugins.external.WatchDog import jiii

# Set the dump location for plugin secrets
SECRET_DUMP = os.path.abspath(os.path.join(os.path.join(os.path.dirname(__file__), "../"), "secrets"))
ensure_path_exists(SECRET_DUMP)

# Get asyncio event loop for subprocess management
ALOOP = asyncio.get_event_loop()

def load(config, plugin, manager):
    """
    Set up the AIGIS plugin. This means executing the two major steps.
    REQUIREMENTS
    RUN

    :param module config: the config module for this plugin
    :param AigisPlugin plugin: the plugin stored in core, regardless of plugin type.
    :param PluginManager manager: this instance's PluginManager

    :raises PluginLoadError: for any problem in loading the plugin
    """
    try:
        contextualize(config, plugin)
        requirements(config, plugin)
        copy_secrets(config, plugin)
        plugin.log.boot("Ready for deployment...")
        run(config, plugin, manager)
    except PluginLoadError as e:
        plugin.log.error(str(e))
        raise


def contextualize(config, plugin):
    """
    Apply any plugin contextualization that could be needed to the config,
    depending on numerous factors.

    :param module config: this plugin's config
    :param AigisPlugin plugin: the plugin stored in core
    """
    if config.PLUGIN_TYPE == 'external':
        config.ENTRYPOINT = config.ENTRYPOINT.format(root=plugin.root)
        config.REQUIREMENT_FILE = config.REQUIREMENT_FILE.format(root=plugin.root)
        config.LAUNCH = config.LAUNCH.format(root=plugin.root)
        for secret in config.SECRETS:
            config.SECRETS[secret] = config.SECRETS[secret].format(root=plugin.root)


def requirements(config, plugin):
    """
    Install the requirements for this plugin on the host system, based on the plugin config.

    :param module config: config module for this plugin
    :param AigisPlugin plugin: the plugin stored in core

    :raises RequirementError: if requirements are not or cannot be met.
    """
    # Check system requirements
    for req in config.SYSTEM_REQUIREMENTS:
        try:
            assert shutil.which(req)
        except AssertionError:
            raise RequirementError("Fatal error. Host has no %s installed." % req)

    try:
        output = os.system(" ".join([config.REQUIREMENT_COMMAND, config.REQUIREMENT_FILE]))
        if output != 0:
            raise RequirementError("Requirement install exited with error code %s" % output)
    except Exception as e:
        raise RequirementError(
            "Could not process requirements %s. The following error occured:\n%s" %
            (config.REQUIREMENT_FILE, str(e))
        )

    plugin.log.boot("Requirements processed successfully...")


def copy_secrets(config, plugin):
    """
    Copy any potential secrets a plugin could have from the AIGIS secret dump to the specified location.
    Will not copy anything is a file is missing.

    :param module config: config module for this plugin
    :param AigisPlugin plugin: plugin registered in core

    :raises MissingSecretFileError: if a specified secret cannot be found.
    """
    missing_secrets = []
    for secret in config.SECRETS:
        if not os.path.exists(os.path.join(SECRET_DUMP, os.path.join(plugin.name, secret))):
            missing_secrets.append(os.path.join(SECRET_DUMP, os.path.join(plugin.name, secret)))
    if not missing_secrets:
        for secret in config.SECRETS:
            shutil.copy2(secret, config.SECRETS[secret])
    else:
        raise MissingSecretFileError("The following secret files are missing:\n" + "\n".join(missing_secrets))


def run(config, plugin, manager):
    """
    This function launches the plugin following different logic depending on the plugin type
    specified in the config.

    :param module config: config module for this plugin
    :param AigisPlugin plugin: plugin to be passed to the WatchDog for external processes
    :param PluginManager manager: this instance's PluginManager to be passed to the WatchDog
    for external processes

    :raises InvalidPluginTypeError: if the plugin type specified in the plugin config is not valid
    """
    if config.PLUGIN_TYPE == "external":
        ALOOP.run_until_complete(_run_external(config, plugin, manager))
        plugin.log.boot("Running...")
    elif config.PLUGIN_TYPE == "core":
        pass
    elif config.PLUGIN_TYPE == "internal":
        pass
    else:
        raise InvalidPluginTypeError("Cannot process plugin type %s." % config.PLUGIN_TYPE)


async def _run_external(config, plugin, manager):
    """
    Launch an asyncio subprocess and request scheduling for the watchdog task.
    """
    proc = await asyncio.create_subprocess_exec(config.LAUNCH, cwd=config.ENTRYPOINT)
    ALOOP.ensure_future(jiii(proc, plugin, manager))


class PluginLoadError(Exception):
    """
    Parent class for plugin load exceptions.
    """

class RequirementError(PluginLoadError):
    """
    Error for issues in handling plugin requirements.
    """

class MissingSecretFileError(PluginLoadError):
    """
    Error to be thrown when a specified secrets file cannot be found.
    """

class InvalidPluginTypeError(PluginLoadError):
    """
    Error when plugin config has an unsupported type.
    """
