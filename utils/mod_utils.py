"""
AIGIS does a lot of runtime module manipulation.
This is a helper module with ease-of-use functions for handling those manueuvers.
"""
import importlib
import os

def import_from_path(config_path):
    """
    Generate a module from a path
    (i.e. import a module using the path to the source file)

    :param str config_path: path to the file to import

    :returns: imported python module
    :rtype: Module
    :raises FileNotFoundError: if the path is not a file
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError("File %s not found on disk" % config_path)
    spec = importlib.util.spec_from_file_location("config", config_path)
    plugin_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin_config)
    return plugin_config
