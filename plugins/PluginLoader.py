"""
Process AIGIS plugin.
"""
import os
import shutil
import traceback
import subprocess

def load(config, plugin):
    """
    Set up the AIGIS plugin. This means executing the two major steps.
    REQUIREMENTS
    RUN

    :param module config: the config module for this plugin
    :param AigisPlugin plugin: the plugin stored in core, regardless of plugin type.
    """
    contextualize(config, plugin)
    requirements(config)
    run(config)


def contextualize(config, plugin):
    """
    Apply any plugin contextualization that could be needed to the config,
    depending on numerous factors.

    :param module config: this plugin's config
    :param AigisPlugin plugin: the core plugin object
    """
    if 'external' in config.PLUGIN_TYPE:
        config.ENTRYPOINT = config.ENTRYPOINT.format(root=plugin.root)


def requirements(config):
    """
    Install the requirements for this plugin on the host system, based on the plugin config.

    :param module config: config module for this plugin

    :raises RequirementError: if requirements are not or cannot be met.
    """
    # Check system requirements
    for req in config.SYSTEM_REQUIREMENTS:
        try:
            assert shutil.which(req)
        except AssertionError:
            raise RequirementError("Fatal error. Host has no %s installed." % req)

    for req in config.REQUIREMENT_LIST:
        try:
            os.system(" ".join([config.REQUIREMENT_COMMAND, req]))
        except Exception as e:
            tb_lines = traceback.format_exception(e.__class__, e, e.__traceback__)
            tb_text = ''.join(tb_lines)
            raise RequirementError(
                "Could not process requirements %s. The following error occured:\n%s" %
                (req, tb_text)
            )

def run(config):
    """
    This function launches the plugin following different logic depending on the plugin type
    specified in the config.

    :param module config: config module for this plugin
    """
    if config.PLUGIN_TYPE == "external":
        subprocess.Popen(config.LAUNCH, cwd=config.ENTRYPOINT)



class RequirementError(Exception):
    """
    Error for issues in handling plugin requirements.
    """
