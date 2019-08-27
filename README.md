# Plugin Types
There are three different logically separate types of plugins that Aigis can run. Due to the fundamentally different nature of each of these types, they are implemented in completely different ways. While some cases may have overlap in execution, there should be no code duplication in theory. At least in a perfectly executed build of a plugin graph.
## Core
Core plugins refer to purely callable, API like chunks of "dead" code. These may extend the functionality of AIGIS as a whole, or may be extra APIs built around other software, but that do not provide any user-facing functionality on their own. For example, zaltu/backdoorgery is something that could be a core plugin, since it simply offers an interface for another program to run independently.

It is of paramount importance that core plugins *do not run on their own, or have self-contained daemon-like attributes*, such as threads, multiprocessing or asyncio event loops. This is because these plugins are loaded as part of the central AIGIS process. Any slow-down or processing power taken from the central process will affect all plugin's responsivity, and should be avoided at all costs. For plugins that interact with the core, but have daemon-like attributes, see the "internal" plugin type.
## Internal
Internal plugins represent most of the active, visible, complex "functionality" of AIGIS. They are plugins that are long-running processes or other daemon-like programs that can interact with each other and with core plugins through AIGIS.

This is why I haven't designed them yet :luigidab: .

__TODO__

## External
External plugins are plugins that run completely independently of the core and do not require any of it's features in order to work. When a plugin is developped without any dependencies on other plugins, it is considered an external plugin.

External plugins can do more or less anything, as they are poped open in an independent subprocess. The only integration for external plugins provided by AIGIS is piping the logs (pulled from stdout and stderr) of the subprocess into AIGIS's central logging system, and optionally restarting on process exit or failure.
