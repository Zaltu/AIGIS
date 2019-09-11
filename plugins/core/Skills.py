"""
Container class for the singleton which holds all core plugins' modules for shared use.
"""

class Skills():
    """
    The skills class is built to mock dynamic runtime inheritance based on loaded plugins.
    Only a single instance of this class should be made, and the private function it exposes
    (_learnskill) should only be called by the core AIGIS code.
    """
    def _learnskill(self, mod, log):
        """
        Join a given dict with this class' dict, essentially extending the functionality of the class.

        :param module mod: a plugin configuration for the CORE plugin type
        :param AigisLogger.log log: plugin's logger
        """
        for name, cls in mod.__dict__.items():
            if name in mod.SKILLS and callable(cls):
                setattr(mod, name, decorator(cls, log))
        toadd = [(name, cls) for name, cls in mod.__dict__.items() if name in mod.SKILLS]
        self.__dict__.update(dict(toadd))


def decorator(f, log):
    """
    Decorator taking any imported callable and wrapping it to include passing the plugin's log.

    :param callable f: function to decorate
    :param AigisLog.log log: log of the plugin

    :returns: the wrapped callable
    :rtype: callable
    """
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
