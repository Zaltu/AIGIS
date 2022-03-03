# Technical ReadMe
This ReadMe exists to shed some light on various technical incongruities and explanations of systems and technologies used in the development of AIGIS. AIGIS is not a simple system by any stretch, and will only get more complicated over time. During development, a strong focus is put on generalization and scalability in order to future-proof the structure of the system as much as possible. The technologies used for this are sometimes not well documented, and the concepts are rarely fully explained, even in official documentation.

To note, when I refer to Python in this doc, I refer specifically to cPython, the standard propagated implementation of Python.

# Python Threading and Asyncio
There's no such thing as multi-threading in Python.
## Python Concurrency Limitations
**Disclaimer, I don't claim to fully understand the backend implementation of cPython. The explanations here may be not entirely correct, or even flat-out wrong.**  
The more specific version, is that there's not such thing as *concurrency using multi-threading* in Python. There's a concept of "frames" in Python where each frame represents a collection of ready-to-interpret Python code which is sent to the interpreter for interpretation. The interpreter itself processes each frame in sequence, using the GIL, Global Interpreter Lock. Presumably, the interpreter needs to lock it's resources to avoid having a total mess when managing the interpretation of each frame, or the resource stack required by each frame, or any other number of things; this part I'm not sure on. The result, however, is that each thread that produces frames sends them to the interpreter, and then one frame at a time gets the GIL and can be actually processed. In practice, this means that because only one frame can be processed at a time, only one thread can actually "run" at a time, thus no actual concurrency. The only thing Python multi-threading offers is to process various sequences of frames (or "threads") in an arbitrary order.

To put this into an actual implementation example, if there were four metrics that needed to be processed, it's the equivalent of needing to decided whether to have 4 metrics at around 25% completion, or two metrics at 100% completion. Since Python multi-threading is *non-concurrent*, it will not actually save time overall, only the distribution of what is processed.

So it's not possible to use threading to achieve concurrency in Python. It is however possible to achieve concurrency using something else: multi-processing. It's simple really, if one Python interpreter can only process things sequencially, just add more interpreters :) . This comes with a whole host of problems on its own of course, primarily the need to pickle/unpickle resources to share accross processes, and the moderate lack of standard library tools to manage semantic locks between processes. (Some of this is detailed in the main ReadMe.) In many cases, just the overhead of needing to boot up another process is significant enough for sequential processing to be more efficient. For long-running operations that require concurrency however, this is usually the correct solution.

## Concurrency VS Coroutines
Coroutines are not concurrent. It seems obvious, but it can be difficult to wrap your head around it when dealing with both in the same program, particularly because of Python's less-than-optimal implementation of the `asyncio` module.
### Concurrency in Theory
In theory, two operations running concurrently are being actively processed by the computer's CPU at the same time, in different cores, hyperthreads, or whatever else CPU manufacturers decide to call them.
### Concurrency in Practice (in Python)
Two different Python processes can be launched, running concurrently as managed by the OS that is managing the processes. At this point Python itself has little conrtol over prioritizing processes.
### Coroutines in Theory
In theory, a coroutine is a normal, blocking process that can be configured to be interrupted while that blocking process is waiting for resources outside of the program's control (Disk write, subprocess response, etc).
### Coroutines in Practice (in Python)
Coroutines in Python actually do exactly that. There are plenty of issues with the implementation of async event loops which will be noted later, but in and of themselves, coroutines in Python allow their process to be interrupted while waiting for a call to finish. In the case of AIGIS, the primary use case of this is using observers to monitor the state of the subprocesses in which Internal and External plugins are launched.

## The Weirdness of Coroutines in Python
Much of the weirdness of the way coroutines are managed in Python comes from the implementation of the "Event Loop" structure that wraps it. The blocking process that manages coroutines is managed by the Event Loop/AbstractEventLoop structures. The implementation of the `asyncio` package further stipulates that only one Event Loop can be running per *thread*. To top it off, launching an Event Loop is *a blocking process in all cases* (`loop.run()`, `loop.run_forever()`, `loop.run_until_complete()`).

The behavior this is trying to encourage, and the workflow supported by official documentation, is that there should only be a single running eventloop in a program (the whole "per-thread" thing being glossed over). The entrypoint of the program should itself be a coroutine, and everything under it as well. This is the primary cause of most `asyncio`-related headaches. **That paradigm just isn't practical.** It effectively forces all code within the program to be async/coroutine.

Why exactly is this a problem? Because it effectly removes the primary benefit of having coroutines in the first place: being able to process other code while waiting for a specific external operation to complete. When an entire codebase is async, `await`ing the end of a coroutine blocks the whole process. Sure, it means Python is idling and not using resources, but it can't process anything else either. Even, using `asyncio.ensure_future()` or `asyncio.create_task()` will queue up the coroutines to run independantly, but so long as the main process doesn't need to `await`, those coroutines will never be run. This means you *must* `await` these coroutines at some point in the main thread, which means blocking the main process.

## The Solution
The solution that's implemented in AIGIS to circumvent this glaring flaw is to focus all `asyncio`/Event Loop operations to a dedicated thread. This way, each coroutine we which to be able to `await` sits inside a single thread running its Event Loop forever, constantly idling the coroutines it's waiting for. This way we have a nice, non-blocking way to submit coroutines that will get processed without needing to "block" the main thread (`asyncio.run_coroutine_threadsafe()`).

## The Thread Caveat
Yes, technically the Event Loop thread and the main thread are not being processed concurrently. However, the primary purpose of using coroutines isn't for concurrency. Especially in the case of AIGIS, the Event Loop after launch will only consist of a bunch of plugin watchdogs idling until the subprocess dies, taking no resources. The addition thread does not behave as overhead.

## The Purpose of Asyncio in AIGIS
So why go through all this trouble in the first place? As with most problems in software development, it all stems from a single function. Specifically, `subprocess.Popen.wait()`. A look at the official Python docs will reveal that this function is implemented "using a busy loop (non-blocking call and short sleeps)". What that means practically is "this thing will slam your CPU for no particular reason while constantly checking if the process is dead". It's the local application equivalent to requesting a DB dump from a server every second rather than using webhooks. As the doc recommends, using `asyncio.subprocess.Process.wait()` is asynchronous, and does not use a busy loop. This is the only (current) use of `asyncio` in AIGIS.

## The AIGIS Thread Caveat
The question to ask would be: if a new Event Loop can be created per thread, why not just have every plugin spawn its own thread and its own Event Loop. Ultimately, since these threads would be idling, the overhead would still be negligable. This cannot be done purely for the reason of the restart/reload feature. Since the subprocess watchdogs must live in an Event Loop, in a thread, the process of attempting to bury, triggering the restart/reload, re-configuring the plugin, and *re-launching it* all happens within the coroutine set up by the previous launch, within that thread. If threads were continuesly spawned every time a plugin was restarted or reloaded, there would end up being child threads of child threads of child threads of child threads of child threads of child threads of child threads of child threads of child threads of child threads of child threads, etc.

This also puts us in a bit of a nasty situation where the environment (and thread) of the process that's launching the plugin is different the first time it launches compared to subsequent times, as subsequent times are triggered from the watchdog residing in the Event Loop thread. Thankfully, the `asyncio.run_coroutine_threadsafe()` function works both inside and outside the thread containing the Event Loop. Unfortunately however, the `Future` object provided by `asyncio.run_coroutine_threadsafe()` is not compatible with `asyncio`, meaning it is not `await`able. This means that in order to run a function that *may or may not be triggered from the Event Loop thread*, it needs to be wrapped in an additional coroutine that uses `asyncio.create_task()` to properly generate an `await`able Future. In essence, the following structure:
```python
# Unknown thread
asyncio.run_coroutine_threadsafe(afunc(), EVENT_LOOP)

async def afunc():
    # Always EVENT_LOOP thread
    future = asyncio.create_task(needtoblock())
    asyncio.create_task(waitforblock(future))

async def needtoblock():
    # Always EVENT_LOOP thread
    pass  # Do stuff

async def waitforblock(future):
    # Always EVENT_LOOP thread
    await future
    print("Woot")  # Do other stuff
```
Again, only Future objects created by `asyncio.create_task()` are `await`able.

### Note on Future/Future
Function signatures are as follows:  
`asyncio.run_coroutine_threadsafe() -> concurrent.futures.Future`
`asyncio.create_task()              -> asyncio.Future`  
While the Future object generated by `asyncio.run_coroutine_threadsafe()` cannot be `await`ed, you can in fact still block the running process to wait for the result using `concurrent.futures.Future.result()`. This function is not compatible with `asyncio` however, so if it is called *within the Event Loop thread*, **the Event Loop thread will block**. This is because coroutines are not concurrent. Because `asyncio` `await` is never called, no pending coroutines are processed and therefore the Event Loop gets stuck forever.


# Issues with Pickle/Dill
TODO, I know I use my slightly modified version of the Dill package for this project, but I forget why... Documentation, amiright?
