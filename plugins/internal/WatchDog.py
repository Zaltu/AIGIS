"""
Helper file to handle watching a *child* processes to completion/crash
"""
import select
import time

def jiiii(plugin, manager):
    """
    Let the OS inform us when a signal is sent to the process sentinel marking the file descriptor
    for the process as "ready".

    Processes should only be terminated if plugins have crashed, or during a manual shutdown. Once
    the main thread reaches the interrupt signal wait in AIGIS.py, the main process should therefore
    be doing almost nothing and take no resources unless called.

    God help me in trying to confirm this, but I believe this is not blocking for a polling time sleep,
    meaning the main thread should be completely unaffected. If not, I'm fucked yo.

    :param AigisPlugin plugin: the plugin corresponding to the process
    :param PluginManager manager: the plugin manager of this AIGIS instance, to bury plugins on death
    """
    # Blocks waiting for OS to recieve correct signal from child process
    select.select([plugin._int_proc.sentinel], [], [])
    # However the OS is faster to respond than the propagation of the signal down to the CPython PyObjects,
    # meaning we should still wait for the exitcode to be populated
    while plugin._int_proc.exitcode is None:
        time.sleep(.01)
    plugin.log.shutdown("Process exited with code %s", plugin._int_proc.exitcode)
    manager.bury(plugin)
