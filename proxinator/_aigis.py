"""
This module holds the local server responsible for handling the incoming RPC calls from internal plugins
running in subprocesses.
"""
from threading import Thread
from multiprocess.managers import SyncManager

import aigis


class AIGISpseq():
    """
    Wrapper class around the logic used to parse the pseq of the requested call.
    A class instance is required by the multiprocess manager library.
    """
    def parse_pseq(self, pseq, *args, **kwargs):
        """
        Endpoint to call any value found in aigis, forwarding the parameters used.

        :param list[str] pseq: point sequence in mainc to follow
        :param args: args to forward
        :param kwargs: kwargs to forward

        :returns: result of final layer
        :rtype: object

        :raises TypeError: if the arguments do not match the requested function's signature.
        """
        toret = self._recurpseq(pseq, 0, aigis)
        if callable(toret):
            toret = toret(*args, **kwargs)
        elif args or kwargs:
            raise TypeError("Too many arguments:\n%s\n%s" % (args, kwargs))
        return toret


    def _recurpseq(self, pseq, i, mod):
        """
        Recursively parse the skills until the end of the point sequence

        :param list[str] pseq: the point sequence
        :param int i: current index
        :param object mod: object on this layer

        :returns: object at the final layer of the point sequence
        :rtype: object
        """
        if i+1 == len(pseq):
            return getattr(mod, pseq[i])
        return self._recurpseq(pseq, i+1, getattr(mod, pseq[i]))


class WrapManager(SyncManager):
    """Wrapper around the multiprocessing manager because classmethods."""
# Register our pseq parsing wrapper class
WrapManager.register("get_aigis", callable=AIGISpseq)

# The Manager object. Runs on localhost:50000
WM = WrapManager(address=("0.0.0.0", 50000), authkey=b"aigis")
# Create a thread for serving the server, since it's blocking.
CORE_SERVER = Thread(target=WM.get_server().serve_forever)
