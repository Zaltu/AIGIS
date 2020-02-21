# AIGIS
Welcome to AIGIS  
```
A - Aggregation of
I - Independently
G - Governed
I - Information
S - Sources
```
## Statement of Purpose and Origins
The goal of AIGIS is to provide a centralized controlling "brain" to act as a link between multiple independently developed systems. In essence, a way of managing the runtimes of multiple programs at once, with centralized information. Based on my experiences, day to day environments tend to slowly become more and more of a spaghettied mess of interdependent relationships over time (technical debt, in a sense). By centralizing the control point of all these dependencies, it becomes much easier to manage missing and otherwise broken dependencies and maintain a clear idea of what is potentially problematic without necessarily needing to keep everything up to date.

It is important to make the distinction between dependency management and runtime management. While AIGIS offers a few tools to flag missing dependencies on bootup, it is the system administrator's responsibility to ensure that all systems are on compatible versions with one another.

AIGIS originated as a means to centralize the monitoring of multiple separately running processes purely because having to regularly double-check a bunch of shells running various independent programs sucks. At it's core, AIGIS was constructed to monitor and provide inter-process services to all these independent systems so that the maintainer would have a simple way to know the state of the environment.

As it progressed, it became apparent that providing more in-depth API services between programs would be hugely beneficial in simplifying the configuration and setup of larger environments. Being able to provide a standard, centralized way of accessing other program's code turned AIGIS into an API service on top of a monitoring one. It's at this point that the concept of "plugins" was formed. Plugins may or may not have dependencies on other plugins, but no matter what requirements it has it does not need to know if or how the dependency is loaded. In fact, the dependency could be a completely differently implemented version of what it expects, but so long as AIGIS can serve the request the plugin won't know.

## Uses
Three grand categories encompass all of the functionality AIGIS is meant to handle. The first is monitoring various completely independent processes in a centralized location, which we refer to as external plugins. The second is to provide a centralized API service where plugins can register their functionality and expose it to the whole of AIGIS, which we refer to as core plugins. The last is to provide runtime environments that include this API service to processes running both locally and remotely, which we refer to as internal plugins. A more in-depth breakdown of each plugin type is offered below, as well as how to set them up and used them to their fullest extent.

## In Short
AIGIS stands as a system to manage the runtime environments of multiple programs. This includes dynamically setting runtime environments, reloading, adding and removing functionality to a core system without the need to halt dependent processes.


# The AIGIS Config File
The AIGIS config file is the place to set which plugins should be run by AIGIS when the system is launched. If no plugins are specified here, AIGIS will do pretty much nothing but sleep in the background forever, so make sure everything you want is set up properly if you want something to happen.

The config file is in TOML format, and separated into three parts: core, internal and external. These correspond to the three different types of plugins available to AIGIS (see section below on Plugin Types). Plugins will always be loaded in the order they are listed within their part. The parts are always loaded in the same sequence, that being
1. core
2. internal
4. external

To define a plugin to get picked up by AIGIS, add a new line in the appropriate part. This line represents  
`plugin_name = plugin_source`  
Where the plugin name is an internal, AIGIS-only, uniquely identifying name that will be used to refer to that plugin on runtime. The plugin source can be one of two things, either a *public* Github HTTPS clone link (the same one you would use to clone a repo locally over HTTPS), or a path on *local* disk leading to the root of the plugin.

The entire AIGIS runtime is determined by this config file, and it must be specified when running the main AIGIS application by passing it as `-c/--config <path_to_aigis.config>`. While it is techinally possible to run multiple instances of AIGIS independently on the same host, it is generally not recommended to do so, as this could lead to many conflicts and overwritten data sources depending on each plugin's implementation.


## Plugin Locations
Plugins can be pulled from two different locations, a public Github HTTPS clone link or a local directory on disk. There is slightly different behavior in each of these cases.

### Github Source
When using a source from github, the specified repo is cloned to the "root" of the plugin's runtime location. Essentially the equivalent of a `git clone` in the directory AIGIS uses to store plugins locally on runtime. AIGIS will always clone the *master branch* of the specified repo. If a plugin has already been cloned in the past, AIGIS will recognize this and attempt the equivalent of a `git fetch` on the cloned repo. If for any reason this fetch fails, it *is not considered an error*. A warning will be logged, noting the plugin could not be updated properly, but it will continue its attempt to load the plugin.

### Local Source
When providing a path to the local source of a plugin, AIGIS will *copy the provided directory* into the plugin's expected runtime location. This is to say that it will __not__ use the location in which the source is provided on runtime. The exact implementation of this is done via `shutil.copytree`, *using default options*. This means symlinks will be followed, permissions will be copied and so on (see the full doc of [shutil.copytree](https://docs.python.org/3.7/library/shutil.html#shutil.copytree) for more info). Should the source already exist in the runtime location, AIGIS will recognize this *and assume the plugin is already present*. Since there is no equivalent function of a `git fetch` for local files, and `shutil.copytree`'s implementation is kinda suck, it will not attempt to update or overwrite the code. This *is not considered an error*. A warning will be logged, noting the plugin could not be updated properly, but it will continue its attempt to load the plugin.

<br>

*Note that in both cases, to __completely__ reset a plugin, you should remove the directory in its name in the plugin runtime directory, generally under `ext/`.*
<br>
<br>

# Requirements
AIGIS is tested under __*Python 3.7.3*__ on __*Linux/Fedora*__ and __*Linux/Ubuntu*__ and is compatible with all Linux and MacOS systems.

Compatibility with Windows is technically possible, however there are many tweaks to make to get it working and it is not a priority. This is unlikely to ever change unless Bill gets his shit together and makes a decent OS.

AIGIS requires the following pip packages, as defined in `requirements.txt`:
- `toml` >= 0.10.0
- `pygit2` == 0.28.*
- `zaltu/dill` == github.com/zaltu/dill
- `multiprocess` == 0.*

These are the requirements for running AIGIS on it's own. Plugins may have other requirements, both executable and through pip. Check your plugin's requirements before launching AIGIS to ensure they can be met.


# Plugin Types
There are three different logically separate types of plugins that Aigis can run. Due to the fundamentally different nature of each of these types, they are implemented in completely different ways. While some cases may have overlap in execution, there should be no code duplication in theory. At least in a perfectly executed build of a plugin graph.


# Core Type
Core plugins refer to purely callable, API like chunks of "dead" code. These may extend the functionality of AIGIS as a whole, or may be extra APIs built around other software, but that do not provide any user-facing functionality on their own. For example, `zaltu/backdoorgery` is something that could be a core plugin, since it simply offers an interface for another program to run independently.

It is of paramount importance that core plugins *do not run on their own, or have self-contained daemon-like attributes*, such as threads, multiprocessing or asyncio event loops. This is because these plugins are loaded as part of the central AIGIS process. Any slow-down or processing power taken from the central process will affect all plugin's responsivity, and should be avoided at all costs. For plugins that interact with the core, but have daemon-like attributes, see the "internal" plugin type.

For obvious reasons, core plugins are required to be written in the same language as AIGIS, currently Python __3.7.3__. While other, similar python versions may be compatible, they will be loaded into this version on runtime.

### Configuring a Core Plugin
Two files are necessary in order to define a core plugin: the plugin config file and the core injector file.
- `{root}/AIGIS/AIGIS.config`: A standard AIGIS config file. See the section on __Aigis Plugin Config File Options__.
- `{root}/AIGIS/AIGIS.core`: Actually a python file defining the symbols for the functionality to be exposed.

### Aigis Core Injector File
Since this functionality is injected directly into the central AIGIS module directly on runtime, there are a few important notes to make concerning their configuration.
1. The File  
The only restriction in the `AIGIS.core` file explicitely is that there exist a `SKILLS` __list type constant__. This constant functions very similarly to the `__all__` standard python constant and has essentially the same syntax: a list of strings denoting the names of the values that you want exposed from your module in the AIGIS core. ONLY the values in `SKILLS` will be exposed in the core. An example of a valid core injection file can be found at then end of this README.
2. Logging  
Since AIGIS uses a central logging system, it is expected that core plugins be compatible with it. When injecting the contents of the AIGIS.core file, AIGIS decorates every *callable* to pass an extra argument parameter, that being a configured and slightly edited version of a python logger. To properly track output in the centralized AIGIS system, it is expected that core plugins use this logger and not any of their own.
3. Inter-core compatibility  
It is a reasonable expectation to be able to call other core modules from a specific plugin. In fact, not being able to do so would in many ways render the entire environment significantly less useful. While there is no way for a plugin itself to ensure that another exists, the whole of the core functionality injected from all plugins is stored within a designated namespace, that is to say `aigis`. So long as you are functioning within the main process (which should generally be the case, since no daemon-like attributes are allowed in core plugins), you can access the namespace in python by doing a simple `import aigis`. You will then be able to call any defined skills from loaded modules from that namespace (eg `aigis.backloggery.getFortuneCookie()`). Please be mindful of plugin load order when doing this however, as *namespace entries are not reserved before injection*. While it is not pythonic, it is suggested that imports on the AIGIS core be done at a class or function level, rather than at module level, if you are worried about load order and plan on importing only specific names.


# Internal Type
Internal plugins represent most of the active, visible, complex "functionality" of AIGIS. They are plugins that are long-running processes or other daemon-like programs that can interact with each other and with core plugins through AIGIS. 

Internal plugins are services with daemon-like attributes that can run on *any* host, *including but not limited to* the host running the AIGIS core. These can be observers, pollers, watchers, or any other variation of such implementation. Of course, they can also do other things, but the AIGIS core will not ever natively make calls to internal plugins, so without some form of external input, they will be functionaly useless.

Internal plugins must be written in the same language, at this moment Python __3.7.3__. The processes handling internal plugins are always launched using the same Python interpreter as the one used to launch AIGIS (via `sys.executable`).

### Configuring an Internal Plugin
Only the central AIGIS config file is *required* in order to configure an internal plugin.
- `{root}/AIGIS/AIGIS.config`: A standard AIGIS config file. See the section on __Aigis Plugin Config File Options__.

Optionally, it is very possible to want to also expose certain internal functionalities of internal plugins to the core, essentially forming a type of hybrid internal/core plugin. In these cases, a core injection file can also be provided.
- `{root}/AIGIS/AIGIS.core`: Actually a python file defining the symbols for the functionality to be exposed.

### Accessing the AIGIS Core from Internal Plugins
AIGIS would be a significantly less useful system if it could not share its registered core functionality accross plugins running on remote hosts. It is undoubtably via internal plugins that users would be able to interact with AIGIS and gain from its centralized information sourcing features. Since internal plugins are not *guarenteed* to run on the same host as the AIGIS core, the system must simulate an environment containing AIGIS, and forward the runtime requests to the core over the network. We refer to the AIGIS exposed in the remote plugin's runtime environment as the AigisProxy. Strictly speaking, the AigisProxy is an infinitely recursive namespace, which forwards calls to the true AIGIS core via a type of RPC. While the exact implementation details aren't suppose to be relevent, this results in a slightly different exposure to the core on runtime.

#### At Its Core
Access to AIGIS in internal plugins is represented as a module, and is called via `import aigis`.

#### The Downside
There are a few important conditions to take into account when calling the core from internal plugins, namely
1. *You can only import the top-level module*  
So you can do `import aigis`, but not `from aigis import amodule` or `import aigis.amodule`. This is because the `aigis` module itself is the AigisProxy which itself does not contain any of the real core's modules itself. Making references in code to `aigis.amodule` outside of the import will only send the request to the true core to evaluate that statement per say.
2. *Everything must be called, including constants*  
The correct way to retrieve the constant integer `MAX_NAME_LENGTH` from the registered module `my_database` is by doing
```python
import aigis

MAX_NAME_LENGTH = aigis.my_database.MAX_NAME_LENGTH()
```
3. *Limited return types*  
If the core function you are calling returns an object that cannot be serialized, an error will be raised. Thanks to the amazing work done by the `dill` and `multiprocess` packages, almost all Python objects, including classes, functions, lambdas and more are all serializable. According to the `dill` documentation, the only types not supported for serialization are [frame, generator and traceback](https://github.com/uqfoundation/dill).

### **Important Notes Concerning Internal-Core Plugin Interaction**
Since it's not necessarily obvious, this section simply servers to shed some light on what can and can't be done when sharing data and functionality accross plugins.

There are two parts to take into account. First of all what functionality can be *exposed*? The simple answer is everything. Any possible functionality, including code related to frames, generators and tracebacks mentioned above, can be called accross process. AIGIS does some magic behind the scenes to make sure that any call made from another process ends up being evaluated *in the core process*. Since core plugins are loaded directly into the core process, this means they are run in a very standard manner, having access to the full scope of their runtimes.

The keyword there is scope, which carries over to part two. What can be *returned/shared* accross processes? Dill explicitely states that frames, generators and tracebacks cannot be serialized (due to relience on the GIL, which I personally know very little about), so those types are, of course, impossible to share. This also means any object or namespace containing these kinds of objects cannot be shared, since they can also not be serialized.  
(As a side note, custom exception types and Exception class objects are still properly raised accross processes. It is only the traceback that cannot be shared, making proper error logging important.)  
Where the scope comes into play is that it is very important to remember that only the *local scope of the returned object* gets serialized. If, for example, a function or class refers at some point to a value that is defined outside of itself, attempting to use that in the subprocess will result in an **`NameError`** if that name is not also defined in the scope of the caller. Some examples:
```python
OUT_OF_SCOPE = ""

<SCOPE> 
        --> def afunction():
        -->     in_scope = 3
        -->     print(in_scope)
        -->     print(OUT_OF_SCOPE)
</SCOPE>

def get_afunction():  # Expose to AIGIS core
    return afunction

# In the subprocess
>>> import aigis
>>> local_afunction = aigis.get_afunction()
>>> local_afunction()
3
Traceback (most recent call last):
  [...]
  File "<stdin>", line 4, in afunction
NameError: name 'OUT_OF_SCOPE' is not defined
>>>
```
If these names are assigned values in the subprocess though, it will work without issue. This should generally be avoided however.
```python
REPLACE_ME = "Don't use this value!"

<SCOPE> 
        --> def afunction():
        -->     inscope = 3
        -->     print(inscope)
        -->     print(REPLACE_ME)
</SCOPE>

def get_afunction():  # Expose to AIGIS core
    return afunction

# In the subprocess
>>> import aigis
>>> local_afunction = aigis.get_afunction()
>>> REPLACE_ME = "Use this one!"
>>> local_afunction()
3
Use this one!
>>> 
```
Again, this is only applicable when `afunction` is *returned by the core and called in the remote process*. If it is called in the core directly, there is no problem.
```python
OUT_OF_SCOPE = "Totally fine"

<SCOPE> 
        --> def afunction():  # Expose to AIGIS core
        -->     inscope = 3
        -->     print(inscope)
        -->     print(OUT_OF_SCOPE)
</SCOPE>

# In the subprocess
# Since it is called in the core process, messages are printed to the core process stdout
>>> import aigis
>>> aigis.afunction()
>>> 
```


## Why Do It This Way?
Generally speaking, and as silly as it sounds, this method was chosen so that the syntaxical manner in which the core is accessed remains the same across all plugin types (the `import aigis` syntax). The alternative would be in the vein of automatically spinning up a REST API service based on registered core plugins, but this would require much greater core plugin configuration and offer less freedom, along with ultimately still creating a number of downsides, namely requiring an HTTP module like `requests` in each internal plugin and having to standardize return types specifically to JSON or another predetermined format.


# External Type
External plugins are plugins that run completely independently of the core and do not require any of its features in order to work. When a plugin is developped without any dependencies on other plugins, it can generally be considered an external plugin.

External plugins can do more or less anything, as they are poped open in a completely independent subprocess. This includes being in a different language than even python. The only integration for external plugins provided by AIGIS natively is piping the logs (pulled from stdout and stderr) of the subprocess into AIGIS's central logging system, and optionally restarting on process exit or failure. Because of that, despite being independent, they still require an AIGIS config file like any other plugin type.

__Note__  
While the AIGIS core does not offer any native support for exchanging data between external plugins, it would be very feasible to create an internal plugin that acts as a REST or other endpoint for the explicit purpose of exposing certain core functionalities to other languages. This is far beyond the scope of the core mainframe however.


# Aigis Plugin Config File Options
The config file to place in each plugin's repo shares a common format across all plugin types. It uses a pythonic syntax to assign values to the default parameters it requires. While the format and location are the same, certain extra options may exist depending on the plugin type. This section gives a breakdown of all possible options and in which contexts they are used.


## ALL PLUGIN TYPES

| Option Name          | Required | Type             | Description |
|:--------------------:|:--------:|:----------------:|-------------|
| PLUGIN_TYPE          | YES      | string           | The plugin's type. Obviously required everywhere. |
| ENTRYPOINT           | YES      | path             | The working directory in which to evaluate anything from this plugin. For internal and external plugins, this will be the working directory set when running the subprocess. For core plugins it is used to make sure imports are functional. |
| SYSTEM_REQUIREMENTS  | NO       | list[string]     | Anything which needs to be installed on the system in order for this plugin to run properly. While it is good practice to state it explicitely, it can be assumed that `python3.7` is available at all times. |
| REQUIREMENTS_COMMAND | NO       | string           | Command to run *in shell* of the host to install language/runtime specific requirements. For python, for example, it will generally be some form of `pip install -r` |
| REQUIREMENTS_FILE    | NO       | path             | File containing list of language-specific package requirements. It is assumed that all languages have a way of loading and installing a list of requirements from a file. |
| SECRETS              | NO       | map[string:path] | Set of secret files to copy from the central AIGIS secret dump to local environments. |
| RESTART              | NO       | int              | Number of times to attempt to restart the plugin if it fails. If RESTART is not defined at all, it will never attempt to restart the plugin. Note that this option is available for core plugins, but generally will not make sense as there should be nothing in a core plugin that requires a "restart" or that would make it "crash". |


## INTERNAL AND EXTERNAL PLUGINS ONLY
Both internal and external plugins use a required parameter called `LAUNCH`. While in both cases it represents the programatical starting point of the application, what that is vairies depending on if it's an internal or external plugin.

| Option Name | Required | Type    | Description |
|:-----------:|:--------:|:-------:|-------------|
| HOST        | NO      | string  | Host on which to run this plugin. Can be `localhost` if desired. Defaults to `localhost`. |
| LAUNCH (EXTERNAL)    | YES      | list[string] | A list of arguments aggregated and executed in the host's command line in order to launch the plugin. For example, `["my_plugin.exe", "-r", "1920"]`. Note that the working directory of the command is set by the ENTRYPOINT required option. | 
|LAUNCH (INTERNAL)     | YES      | module name         | Importable sequence to the Python file containing the plugin's launch function, relative to the ENTRYPOINT given (used to import the launch file, eg `main` -> `import main`). The function __*MUST* have the signature__ `def launch()`. Anything sent to `stdout` or `stderr` will be automatically captured and logged. |


## Config File Perks
Some extra processing is done on config files in order to offer some quality-of-life improvements when writing config files. These changes are listed below.

### Secret Storage
Secrets are an important part of securing any application. To avoid having to commit and push hidden files, or perform weird manual manipulations on runtime paths, AIGIS offers a secure, secret distribution method.

Secrets should be placed *on local disk* in the directory `secrets/<plugin_name>` at the *top level* of the AIGIS code, where `<plugin_name>` is the name set in the AIGIS configuration file (found in `config/config.aigis`). These secrets can be copied on runtime to a location within the plugin's source code using the SECRETS config option detailed above.

### `{root}`
Plugins are all loaded into a certain place on runtime that isn't necessarily apparent to the config file author. Since many parameters expect path-like entries, the keyword `{root}` is formatted with the local path on disk leading to the plugin. So for example to get to the `src` file of a plugin with an internal structure of `python/AIGIS/src.py`, you can specify `{root}/python/AIGIS/src.py`. This is only done on certain specific configuration options, since many do/should not require it. The supported options for `{root}` are:
- ENTRYPOINT
- REQUIREMENTS_FILE
- SECRETS (only the value, not the key)
- LAUNCH (applicable for internal plugins)

### `cleanup`
Certain plugins may understandably have some more complex resources loaded in order to provide more complex services. In this case, it's important to be able to specify a certain way of liberating these resources in the event that AIGIS is shut down while these resources are in use. To do this, a special keyword is processed when loading *core* functionalities (from both core plugins and internal plugins with core hooks). That keyword is `cleanup`. When a core file defines the skill `cleanup`, the value will be registered internally to the AIGIS system and called on program exit. If it does not exist, no cleanup will be done outside the usual Python resource closure. Note that cleanup is expected to be a function and will be *called* on exit. Test these function thoroughly, as their failure may have serious unwanted effects.


# Testing
Considering AIGIS is a distributed system, testing multiple dependencies can seem rather difficult, and it is indeed a little non-standard. Since multiple core plugins could rely on each other, and setting up a simulated environment with all the path management done by AIGIS is quite a pain, the best way to test AIGIS plugins is by spinning up a test AIGIS instance, loading only the plugins needed to test.

This can still be a problem when testing core plugins however. Since by design they have no interactivity, there must be at least one internal plugin in order to test the behavior of core plugins. So that there's no need to create a personalized internal plugin just for testing, AIGIS provides a default, AIGIS compliant terminal solution for loading the active AIGIS environment into any interpreter session. Simply import the `AIGISTerminal` file found in `tests`, then import `aigis`.

```bash
zaltu@mercy tests $ python3.7
Python 3.7.3 (default, May 13 2019, 11:43:03) 
[GCC 4.8.5 20150623 (Red Hat 4.8.5-16)] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import AIGISTerminal
>>> import aigis
>>> aigis.backloggery.getFortuneCookie("zaltu")
'Time to play some God of War III (PS4), my dude!'
```


# Example Config Files

## For Core Plugin
### AIGIS.config
```python
PLUGIN_TYPE = "core"
ENTRYPOINT = "{root}"

SYSTEM_REQUIREMENTS = ["pip3.7"]

REQUIREMENT_COMMAND = "pip3.7 install --user --index-url https://pypi.python.org/simple -r"
REQUIREMENT_FILE = "{root}/requirements.txt"

SECRETS = {}
```
### AIGIS.core
```python
"""
Define names to export to AIGIS
"""
import mymodule.somecode as coolstuff

SKILLS = ["coolstuff.firstcoolthing", "coolstuff.secondcoolthing"]
```

## For Internal Plugin
### AIGIS.config
```python
PLUGIN_TYPE = "internal"
ENTRYPOINT = "{root}"
LAUNCH = "main"

SYSTEM_REQUIREMENTS = ["pip3.7", "ffmpeg"]

REQUIREMENT_COMMAND = "pip3.7 install --user --index-url https://pypi.python.org/simple -r"
REQUIREMENT_FILE = "{root}/requirements.txt"

SECRETS = {
    "super.secret": "{root}/secrets/gcreds/"
}
```

## For External Plugin
### AIGIS.config
```python
PLUGIN_TYPE = "external"
ENTRYPOINT = "{root}"
LAUNCH = ["python36", "main.py"]

SYSTEM_REQUIREMENTS = ["python36", "pip3.6"]

REQUIREMENT_COMMAND = "pip3.6 install -r"
REQUIREMENT_FILE = "{root}/requirements.txt"

SECRETS = {
    "my_app_key.secret": "{root}/src/db/",
    "ip.config": "{root}/src/db/",
    "connection_token.secret": "{root}/src/db/"
}
```
