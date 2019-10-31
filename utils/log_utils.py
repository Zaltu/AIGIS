"""
Container module for logging utility functions.
"""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

from utils import path_utils  #pylint: disable=no-name-in-module

def _plugin_file_name(plugin):
    """
    Fetch the filename of a plugin's log file.

    :param AigisPlugin plugin: an AigisPlugin

    :returns: absolute log file path
    :rtype: str
    """
    return os.path.abspath(
        os.path.join(
            path_utils.PLUGIN_LOG_LOCATION,
            "_".join([plugin.name, str(plugin.id)]) + ".log")
    )


def _add_log_handlers(logger, logfile):
    """
    Add the file and stream handlers to a logger.

    :param logging.logger logger: the logger to configure
    :param str logfile: file to log to disk

    :returns: the rotating file handler, used for subprocess logging.
    :rtype: FileHandler
    """
    path_utils.ensure_file_exists(logfile)
    logger.setLevel(logging.INFO)
    fh = TimedRotatingFileHandler(logfile, when="midnight", backupCount=3)
    fh.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s : %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(_SH)
    return fh


### Define extra custom logging levels.
### Mostly used for fluff, but potentially usefull also for log tracking and management.
### We define BOOT and SHUTDOWN here.
BOOTUP = logging.ERROR + 1
logging.addLevelName(BOOTUP, "BOOT")
def boot(self, message, *args, **kws):  #pylint: disable=missing-docstring
    if self.isEnabledFor(BOOTUP):
        # Yes, logger takes its '*args' as 'args'.
        self._log(BOOTUP, message, args, **kws)
logging.Logger.boot = boot


SHUTDOWN = logging.ERROR + 2
logging.addLevelName(SHUTDOWN, "SHUTDOWN")
def shutdown(self, message, *args, **kws):  #pylint: disable=missing-docstring
    if self.isEnabledFor(SHUTDOWN):
        # Yes, logger takes its '*args' as 'args'.
        self._log(SHUTDOWN, message, args, **kws)
logging.Logger.shutdown = shutdown


path_utils.ensure_path_exists(path_utils.LOG_LOCATION)
path_utils.ensure_path_exists(path_utils.PLUGIN_LOG_LOCATION)


_SH = logging.StreamHandler(sys.stdout)
_SH.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s : %(message)s'))


LOG = logging.getLogger("AIGIS")
_add_log_handlers(LOG, os.path.join(os.path.dirname(__file__), "../log/core.log"))
