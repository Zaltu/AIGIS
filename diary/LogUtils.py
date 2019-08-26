"""
Container module for logging utility functions.
"""
import os
import sys
import logging

from utils.path_utils import ensure_file_exists  #pylint: disable=no-name-in-module

def _plugin_file_name(plugin):
    """
    Fetch the filename of a plugin's log file.

    :param AigisPlugin plugin: an AigisPlugin

    :returns: absolute log file path
    :rtype: str
    """
    return os.path.abspath(
        os.path.join(
            PLUGIN_LOG_LOCATION,
            "_".join([plugin.name, str(plugin.id)]) + ".log")
    )


def _add_log_handlers(logger, logfile):
    """
    Add the file and stream handlers to a logger.

    :param logging.logger logger: the logger to configure
    :param str logfile: file to log to disk
    """
    ensure_file_exists(logfile)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile)
    fh.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s : %(message)s'))
    logger.addHandler(fh)
    logger.addHandler(_SH)


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


PLUGIN_LOG_LOCATION = os.path.join(os.path.dirname(__file__), "../log/plugins/")
CORE_LOG_LOCATION = os.path.join(os.path.dirname(__file__), "../log/{corename}.log")


_SH = logging.StreamHandler(sys.stdout)
_SH.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s : %(message)s'))


if not os.path.exists(os.path.abspath(os.path.join(os.path.dirname(__file__), "../log"))):
    os.mkdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "../log")))


LOG = logging.getLogger("AIGIS")
_add_log_handlers(LOG, os.path.join(os.path.dirname(__file__), "../log/core.log"))
