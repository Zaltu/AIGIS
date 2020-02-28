"""
Container module for "abstract" exception classes so they can be easily depended on by any module.
This was so I never need to worry about interdependancies caused by silly exception class proxies.
"""

class PluginLoadError(Exception):
    """
    Parent class for plugin load exceptions.
    """
