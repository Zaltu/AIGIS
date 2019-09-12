# Plugin Types
There are three different logically separate types of plugins that Aigis can run. Due to the fundamentally different nature of each of these types, they are implemented in completely different ways. While some cases may have overlap in execution, there should be no code duplication in theory. At least in a perfectly executed build of a plugin graph.

# Core Type
Core plugins refer to purely callable, API like chunks of "dead" code. These may extend the functionality of AIGIS as a whole, or may be extra APIs built around other software, but that do not provide any user-facing functionality on their own. For example, zaltu/backdoorgery is something that could be a core plugin, since it simply offers an interface for another program to run independently.

It is of paramount importance that core plugins *do not run on their own, or have self-contained daemon-like attributes*, such as threads, multiprocessing or asyncio event loops. This is because these plugins are loaded as part of the central AIGIS process. Any slow-down or processing power taken from the central process will affect all plugin's responsivity, and should be avoided at all costs. For plugins that interact with the core, but have daemon-like attributes, see the "internal" plugin type.

Unlike internal and external plugins, core plugins are required to be written in the same language as AIGIS, currently __3.7.3__

### Configuring a Core Plugin
Two files are necessary in order to define a core plugin: the plugin config file and the core injector file.
- `{root}/AIGIS/AIGIS.config`: A standard AIGIS config file. See the section on __Aigis Config File Options__.
- `{root}/AIGIS/AIGIS.core`: Actually a python file defining the symbols for the functionality to be exposed.

### Aigis Core Injector File
Since this functionality is injected directly into the central AIGIS module directly on runtime, there are a few important notes to make concerning their configuration.
1. The File:
The only restriction in the `AIGIS.core` file explicitely is that there exist a `SKILLS` __list type constant__. This constant functions very similarly to the `__all__` standard python constant and has essentially the same syntax: a list of strings denoting the names of the values that you want exposed from your module in the AIGIS core. ONLY the values in `SKILLS` will be exposed in the core.
2. Logging:
Since AIGIS uses a central logging system, it is expected that core plugins be compatible with it. When injecting the contents of the AIGIS.core file, AIGIS decorates every *callable* to pass an extra argument parameter, that being a configured and slightly edited version of a python logger. To properly track output in the centralized AIGIS system, it is expected that core plugins use this logger and not any of their own.

# Internal Type
Internal plugins represent most of the active, visible, complex "functionality" of AIGIS. They are plugins that are long-running processes or other daemon-like programs that can interact with each other and with core plugins through AIGIS.

This is why I haven't designed them yet :luigidab: .

__TODO__

# External Type
External plugins are plugins that run completely independently of the core and do not require any of it's features in order to work. When a plugin is developped without any dependencies on other plugins, it is considered an external plugin.

External plugins can do more or less anything, as they are poped open in an independent subprocess. The only integration for external plugins provided by AIGIS is piping the logs (pulled from stdout and stderr) of the subprocess into AIGIS's central logging system, and optionally restarting on process exit or failure (TODO).
