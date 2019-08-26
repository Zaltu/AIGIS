"""
Helper file to handle watching the processes to completion/crash
"""

async def jiii(proc, plugin, manager):
    """
    Asynchroneously watch the state of all subprocesses launched. When one is terminated,
    process it accordingly.

    Processes should only be terminated if plugins have crashed, or during a manual shutdown,
    meaning the event loop should be able to yield the process almost all the time. Once the
    main thread reaches the interrupt signal wait in AIGIS.py, the main process should therefore
    be doing almost nothing and take no resources unless called.

    :param asyncio.subprocess.Process proc: a subprocess with an async `wait` implementation
    :param AigisPlugin plugin: the plugin corresponding to the process
    :param PluginManager manager: the plugin manager of this AIGIS instance, to bury plugins on death
    """
    await proc.wait()
    plugin.log.SHUTDOWN("Process exited with code %s", proc.returncode)
    manager.bury(plugin)
