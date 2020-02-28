"""
Container file for path management utilities.
"""
import os

# Constant paths
# Plugins
PLUGIN_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ext"))
REMOTE_PLUGIN_ROOT_PATH = DEFAULT_REMOTE_ROOT = "./sam_test/remote/"
SECRET_DUMP = os.path.abspath(os.path.join(os.path.join(os.path.dirname(__file__), "../"), "secrets"))
# Proxinator
PROXI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../proxinator/injector/aigis.py"))
REMOTE_PROXI_PATH = "./sam_test/remote/_AIGISProxy/aigis.py"
# Logging
LOG_LOCATION = os.path.abspath(os.path.join(os.path.dirname(__file__), "../log"))
PLUGIN_LOG_LOCATION = os.path.abspath(os.path.join(os.path.dirname(__file__), "../log/plugins/"))

def ensure_path_exists(path):
    """
    If provided path does not exist, create it.

    :param str path: path to validate

    :returns: if path existed
    :rtype: bool
    """
    # Ensure that the plugin download path exists
    if not os.path.exists(path):
        os.makedirs(path)
        return False
    return True


def ensure_file_exists(path):
    """
    If file does not exist, ensure that the path to the file exists, then create the file

    :param str path: path to file
    """
    if not os.path.exists(os.path.dirname(path)):
        ensure_path_exists(os.path.dirname(path))
    if not os.path.exists(path):
        with open(path, 'w+'):
            pass
