"""
Representation of a plugin with handlers used by the core to properly route traffic.
"""

class AigisPlugin():
    """
    A plugin that can be managed by AIGIS and it's core.
    """
    def __init__(self):
        self.id = id(self)
        self.name = None
        self.type = None

    def __eq__(self, other):
        """
        Determine if two plugins are the same based on their attributed UID.
        This only works between two AigisPlugin objects. Otherwise will return false.

        :param AigisPlugin other: other plugin against which to check

        :returns: boolead equivalence
        :rtype: bool
        """
        try:
            return self.id == other.id
        except AttributeError:
            pass
        return False
