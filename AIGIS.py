"""
Application entrypoint.
"""
import os
import signal
from argparse import ArgumentParser
from threading import Event
from core.AigisCore import Aigis  #pylint: disable=no-name-in-module

SHUTDOWN_EVENT = Event()
DEFAULT_CONFIG = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "config.aigis"))

def main():
    """
    Boot up Aigis core.
    """
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='cpath', help='Config file path', default=DEFAULT_CONFIG)
    options = parser.parse_args()

    # Insure any interrupt is handled smoothly.
    signal.signal(signal.SIGINT, lambda a, b: SHUTDOWN_EVENT.set())

    # Launch Aigis
    Aigis(options.cpath)

    # Wait for shutdown event
    SHUTDOWN_EVENT.wait()


if __name__ == "__main__":
    main()
