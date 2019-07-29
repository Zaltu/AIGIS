"""
Responsible for the logging environment used both by the core and by the plugins
that pipe their outputs to the core.
"""
import logging
from collections import deque

from utils.LogUtils import _add_log_handlers, _plugin_file_name, LOG  #pylint: disable=no-name-in-module


class AigisLogger():
    """
    Substitute class for logging with funcitonality depending on the plugin type.

    Be warned that for the case of external processes whose stdout pipes we catch,
    we open a file handler that is not automatically closed. It is up to the plugin
    watchdog to cleanup internal systems should a plugin crash or otherwise terminate.

    :param AigisPlugin plugin: plugin for which to create the logger
    """
    filehandler = None
    logger = None
    log_file = None
    def __init__(self, plugin):
        self.log_file = _plugin_file_name(plugin)
        if plugin.type == "external-pipe":
            self.filehandler = open(self.log_file, 'a+')
        elif plugin.type in ["internal", "core"]:
            self.logger = logging.getLogger(plugin.name)
            _add_log_handlers(self.logger, self.log_file)

    def tail(self):
        """
        Fetch the last 5 logs of a certain plugin.

        :returns: last 5 or fewer logs in the log file.
        :rtype: list
        """
        try:
            with open(self.log_file, 'r') as f:
                endlogs = deque(f, 5)
            return endlogs
        except IOError:
            LOG.warning("File %s does not exist. Cannot tail.", self.log_file)

    def cleanup(self):
        """
        Make sure all relevent open IO pipes are closed.
        """
        if self.filehandler:
            self.filehandler.close()
