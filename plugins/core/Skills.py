"""
Container class for the singleton which holds all core plugins' modules for shared use.
"""
#pylint: disable=invalid-name,import-error
from utils import exc_utils


class Skills():
    """
    The skills class is built to mock dynamic runtime inheritance based on loaded plugins.
    Only a single instance of this class should be made, and the private functions it exposes
    (_AIGISlearnskill and _AIGISrecurdict) should only be called by the core AIGIS code.

    AIGISReload is intentionally exposed to allow plugins to request others to reload themselves.

    :param PluginManager manager: the plugin manager singleton
    """
    def __init__(self, manager):
        self.__plugin_manager__ = manager

    def AIGISReload(self, plugin_name):
        """
        Request AIGIS to reload a certain plugin.
        If a plugin tries to self-reload, it might have a bad time.

        :param str plugin_name: name of plugin to reload
        """
        for plugin in self.__plugin_manager__:
            if plugin.name == plugin_name:
                plugin.loader.reload(plugin, self.__plugin_manager__)
                break

    def _AIGISlearnskill(self, mod, plugin):
        """
        Join a given dict with this class' dict, essentially extending the functionality of the class.

        :param module mod: module who's functionality to port
        :param AigisPlugin plugin: this AigisPlugin
        """
        for name in mod.SKILLS:
            pseq = name.split(".")
            self._AIGISrecurdict(mod, pseq, 0, self, plugin.log)
            plugin.log.boot("Registered %s...", name)

        # If the core plugin has exposed a way to perform a cleanup of it's resources, mark that in the
        # AigisPlugin to be called on program exit.
        if hasattr(mod, "cleanup"):
            plugin.cleanup = mod.cleanup

    def _AIGISforgetskill(self, mod, plugin):
        """
        Remove the attributes from a module that were loaded into this class.
        Somewhat dangerous to call, obviously. Should only be called as part of reloading a core module, and
        all that entails.

        :param module mod: module who's functionality to port
        :param AigisPlugin plugin: this AigisPlugin
        """
        top_level_removed = []
        for name in mod.SKILLS:
            pseq = name.split(".")
            if pseq[0] in top_level_removed:
                plugin.log.debug("Name %s deregistered by pruning.", name)
                continue
            try:
                delattr(self, pseq[0])
                top_level_removed.append(pseq[0])
            except AttributeError:
                plugin.log.error("Attempted to deregister %s, which cannot be found in the core.", pseq[0])
                continue
            plugin.log.warning("Deregistered %s and everything downstream.", pseq[0])

    def _AIGISrecurdict(self, mod, pseq, i, ns, log):
        """
        False recursivity to parse the point sequence of the submitted injection and copy the
        attributes into a namespace proxy within this Skills instance.

        Do NOT call randomly.

        :param object mod: object at this layer of the point sequence
        :param list[str] pseq: the complete point sequence
        :param int i: current point sequence index
        :param object ns: _Namespace or parent module in which to add the current point sequence object
        :param logging.logger log: the injecting AigisPlugin's logger for decorating callables

        :raises NamespaceLockError: if the point sequence cannot be followed. While this could be
        some meme python thing, most times it is probably because of a typo or logic error in the
        injector file's SKILLS list.
        """
        if i+1 == len(pseq):
            setattr(ns, pseq[i], decorator(getattr(mod, pseq[i]), log))
            return
        if pseq[i] in dir(mod):
            if pseq[i] in dir(ns):
                self._AIGISrecurdict(getattr(mod, pseq[i]), pseq, i+1, getattr(ns, pseq[i]), log)
            else:
                setattr(ns, pseq[i], _Namespace())
                self._AIGISrecurdict(getattr(mod, pseq[i]), pseq, i+1, getattr(ns, pseq[i]), log)
            return
        raise NamespaceLockError(
            "Module path %s cannot be followed. Cannot find %s in %s...\n%s" %
            (".".join(pseq), pseq[i], mod, dir(mod))
        )


class _Namespace():
    """
    Container class namespace for rebuilding point sequences
    """


class NamespaceLockError(exc_utils.PluginLoadError):
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
        Call the callable with the plugin's log as named argument. If a TypeError is raised, quickly
        check if it may be due to the injected function not supporting the "log" parameter and retry.
        All other errors bubble up...

        :param args: the callable's args
        :param kwargs: the callable's kwargs

        :returns: the return of the callable
        :rtype: unknown

        :raises TypeError: if a TypeError is raised from the called function, unless it is due to
        not supporting the "log" parameter
        """
        try:
            return f(*args, logger=log, **kwargs)
        except TypeError as e:
            if "unexpected keyword argument 'logger'" in str(e):
                log.warning("Function %s called without AIGIS logging...", str(f))
                return f(*args, **kwargs)
            raise
    return internal
