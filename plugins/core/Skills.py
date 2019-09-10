"""
Container class for the singleton which holds all core plugins' modules for shared use.
"""
import types
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
        """
        toadd = [(name, cls) for name, cls in mod.__dict__.items() if name in mod.SKILLS]
        for name, cls in toadd.items():
            if isinstance(cls, types.FunctionType):
                setattr(mod, )
        self.__dict__.update(dict(toadd))
