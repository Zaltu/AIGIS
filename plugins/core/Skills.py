"""
Container class for the singleton which holds all core plugins' modules for shared use.
"""

class Skills():
    """
    The skills class is built to mock dynamic runtime inheritance based on loaded plugins.
    Only a single instance of this class should be made, and the private functions it exposes
    (_AIGISlearnskill and _AIGISrecurdict) should only be called by the core AIGIS code.
    """
    def _AIGISlearnskill(self, mod, log):
        """
        Join a given dict with this class' dict, essentially extending the functionality of the class.

        :param module mod: a plugin configuration for the CORE plugin type
        :param AigisLogger.log log: plugin's logger
        """

        for name in mod.SKILLS:
            try:
                # Initialize namespace traversing objects
                pseq = name.split(".")
                i = 0
                leafdict = mod
                # Deal with the top-level namespace if we can.
                # This prevents us from having to generate a namespace buffer object for everything
                if pseq[i] in leafdict.__dict__:
                    leafdict = getattr(mod, pseq[i])
                    i += 1
                # Recursively traverse the rest of the point sequence
                leafdict = self._AIGISrecurdict(leafdict, pseq, i)
                # Set the branch as a self attribute. Don't forget to decorate callables with the logger
                setattr(self, pseq[0], decorator(leafdict, log))
                log.boot("Registered %s", name)
            except NamespaceLockError as e:
                log.error(str(e))

    def _AIGISrecurdict(self, mod, pseq, i):
        """
        Recursively parse the given module based on the point sequence given and return a
        callable namespace containing the full path to the injected object.

        Do NOT call this randomly

        :param object mod: object namespace to parse this round
        :param list pseq: list of dot-separated values denoting the injection path
        :param int i: current index in pseq, initially 0

        :returns: namespace path to injected object
        :rtype: object
        :raises NamespaceLockError: if the point sequence cannot be followed in the injected namespace
        """
        if i == len(pseq):
            # Exit condition, we've reached the end of the point sequence
            return mod
        if pseq[i] in dir(mod):
            ns = _Namespace()
            setattr(ns, pseq[i], getattr(mod, pseq[i]))
            return self._recurdict(ns, pseq, i+1)
        # The entry in the point sequence for this index can't be found in this namespace layer...
        # This could be some weird python thing, but more likely someone typoed or incorrectly
        # imported their values in their injector file.
        raise NamespaceLockError("Module path %s cannot be followed" % ".".join(pseq))


class _Namespace():
    """
    Container class namespace for rebuilding point sequences
    """

class NamespaceLockError(Exception):
    """
    Error for when a requested importable cannot be found within
    the layered namespaces of the injection module
    """


def decorator(f, log):
    """
    Decorates f to include passing the plugin's log
    Decorator taking any imported callable and wrapping it to include passing the plugin's log.

    :param callable f: function to decorate
    :param AigisLog.log log: log of the plugin

    :returns: the wrapped callable
    :rtype: callable
    """
    if not callable(f):
        return f
    def internal(*args, **kwargs):
        """
        Call the callable with the plugin's log as named argument

        :param args: the callable's args
        :param kwargs: the callable's kwargs

        :returns: the return of the callable
        :rtype: unknown
        """
        return f(log=log, *args, **kwargs)
    return internal
