"""
This is just a slimmed version of the injector from proxinator/injector.
It can be used to simulate the environment of an internal plugin at any time.
"""
import sys
from multiprocess.managers import SyncManager


class _WrapManager(SyncManager):
    """
    Simple wrapper around SyncManager for cleanliness because classmethods
    """
# Register the pseq processing function
_WrapManager.register("get_aigis")
_WMGR = _WrapManager(address=("0.0.0.0", 50000), authkey=b"aigis")
_WMGR.connect()
_REMOTE_AIGIS_CORE = _WMGR.get_aigis()


def _inject(pseq, *args, **kwargs):
    """
    Underlying RPC logic powering the transfer. Connect to the RPC port and fetch the remote processor proxy,
    then pass it the pseq. It will return the result of the pseq processing.

    :param list pseq: the point sequence to call
    :param args: the args to pass to the pseq
    :param kwargs: the kwargs to pass to the pseq

    :returns: whatever the remote processing of the pseq returns, if it is a valid type
    :rtype: object
    """
    return _REMOTE_AIGIS_CORE.parse_pseq(pseq, *args, **kwargs)

class _AIGISCopyCat():
    """
    Copycat class structure that can be called on any pseq.
    Unfortunately requires a call to do anything, since there's no real way of knowing when the last element
    of the pseq is getting added.
    """
    def __init__(self):
        self.pseq = []

    def __call__(self, *args, **kwargs):
        """
        Denotes that a point in the pseq is getting called, so it runs the injection, ultimately forming an
        RPC call to the server with the current pseq.

        :param args: args to pass to the server
        :param kwargs: kwargs to pass to the server

        :returns: the return of the injected call from the server
        :rtype: object
        """
        return _inject(self.pseq, *args, **kwargs)

    def __getattr__(self, attr):
        """
        Allows the copycat class to store the full requested pseq when receiving a call. In reality, calling
        a pseq on the copycat only ever returns itself, it simply logs that a string attribute was requested
        so the info can be passed on when it is eventually called.

        :param str attr: the attribute requested

        :returns: self, the current copycat object
        :rtype: _AIGISCopyCat
        """
        self.pseq.append(attr)
        return self


class _AIGISProxy():
    """
    Wrapper class around the _AIGISCopyCat namespace to ensure that each call's pseqs don't get mixed up.
    """
    def __getattr__(self, attr):
        """
        Override of getattr to generate a copy of _AIGISCopyCat to be used to generate this call's pseq.

        :param str attr: starting point's seq

        :returns: the _AIGISCopyCat object at the correct pseq for further processing
        :rtype: _AIGISCopyCat
        """
        return _AIGISCopyCat().__getattr__(attr)


# Syntaxical sugar that lets the proxy be called using a nice name that's consistent accross the AIGIS system
sys.modules["aigis"] = _AIGISProxy()
