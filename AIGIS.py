"""
Application entrypoint.
"""
from argparse import ArgumentParser
from core.AigisCore import Aigis  #pylint: disable=no-name-in-module


def main():
    """
    Boot up Aigis core.
    """
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', dest='cpath', help='Configuration file path', required=True)
    options = parser.parse_args()

    Aigis(options.cpath)


if __name__ == "__main__":
    main()
