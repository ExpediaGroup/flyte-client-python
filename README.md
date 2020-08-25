# flyte-client

flyte-client is a python library designed to make the writing of flyte packs simple. 
The client handles the registration of a pack with the flyte server, consuming and handling command actions, and gives the ability to send
pack events to the flyte server. This allows the pack writer to concentrate solely on the functionality of their pack.


## Getting started

* Clone this repo
* Run `make prepare-dev` only once (must have python3 installed )
* Run `make init` to setup virtualenv and download all the dependencies.

#### Classes
The classes that a pack developer interacts with can be found in `flyte/pack/classes.py`.
The main ones are as follows:

- **PackDef**: defines the pack - it's name, what commands it has and what events it can raise.
- **EventDef**: defines an event - it's name and an optional help URL to describe the event in more detail
- **Command**: defines a command that can be called on the pack - its name, what event it returns, and an optional help URL to describe the event in more detail. 
Also includes a **CommandHandler** which is the function that will be executed when the command is called.
- **Event**: this dto is sent from the pack to the flyte server api - it contains the name of the event and it's payload 


#### Events

Packs can send events to the flyte server in 3 ways:

1. The pack can observe something happening and spontaneously send an event to the flyte server. 
For example a chat-ops pack, may observe an instant message being sent and raise a "MessageSent" event to the flyte server. 
It would do this by calling the `send_event` function on the `Pack` class.

1. A flow on the flyte server creates an action for the pack to execute. 
The client will poll for this action and invoke the relevant `CommandHandler` that the pack dev has defined. 
This handler will return an event that the client will then send to the flyte server. 
For example the same IM pack as above may have a 'sendMessage' command that would return either a 'MessageSent' or 'MessageSendFailure' event.

1. The client will produce `FATAL` events as a result of panic happening while handling a `Command`. This will be intercepted by the
client and it will recover. If they need to, packs can also produce `FATAL` events themselves as a result of the handling if they detect
any errors using `NewFatalEvent(payload interface{})`. This is preferred over throwing an exception in the handler. E.g.
```python
class MyCommandHandler(CommandHandler):
    def handle(self, request) -> Event:
        ...
        """Preferred""" 
        event = fatal_event("Error message")
        """Over"""
        raise Exception("something went wrong")
        ...
```

The 'EventDefs' field on a Command is mandatory.
The 'EventDefs' on the PackDef are optional. Here you would specify any events that the pack observes and sends spontaneously. 
If the event you want to define is already defined in a command (as with 'MessageSent' above) then you are not required to add it to the separate EventDefs section - however there is no harm in doing so.

#### Help URLs

You will notice that a `helpURL` field is present in 3 locations - PackDef, Command, and EventDef. 
These correspond to the URLs visible in the json on the flyte server at that level.
The help URLs are all optional, though you should generally always have the pack level one. 
It's up to pack developers to provide which ones they think are the most useful. 
For a simple pack you'd probably just provide a single pack level help link. 
For a more complex pack you might want to deep link commands & event definitions to a specific piece of documentation.

The URL should link to a page that describes what a flow writer needs to know i.e. what the pack does, the format of the json in the event payloads and the format of the json for command inputs.
It's up to the pack dev where and how they host their help docs - for example it could be a link to a README file or a hosted web page.

#### Example Pack

The example below shows how to create a pack. The pack exposes a "Rota" command allowing users to query for who is on duty.
If this command succeeds it returns an "RotaRetrieved" event.


```python
import asyncio
import functools
import logging
import os
import random
import signal

from flyte import Pack
from flyte.client.client import Client
from flyte.pack.classes import PackDef, Command, EventDef, CommandHandler, Event


class RotaCommandHandler(CommandHandler):
    """command handler that process rota commands"""

    def __init__(self, log) -> None:
        self.logger = log

    def handle(self, request) -> Event:
        candidates = ["Isaac", "Jane", "Tom", "Lukas", "Emilie"]
        self.logger.info("message successfully consumed")
        return Event(eventDef=EventDef(name="RotaRetrieved"), payload=random.choice(candidates))


def shutdown(event_loop):
    logger.info('received stop signal, cancelling tasks...')
    for task in asyncio.Task.all_tasks():
        task.cancel()
    logger.info('bye, exiting in a minute...')
    event_loop.stop()


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.addHandler(logging.StreamHandler())

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, functools.partial(shutdown, loop))
    loop.add_signal_handler(signal.SIGHUP, functools.partial(shutdown, loop))

    try:
        pack_def = PackDef(
            name="page-of-duty-pack",
            commands=[
                Command(name="Rota", handler=RotaCommandHandler(logger), output_events=[
                    EventDef(name="RotaRetrieved"),
                    EventDef(name="Error"),
                ]),
            ],
            labels={},
            event_defs=[],
            help_url="http://github.com/your-repo.git")

        pack = Pack(pack_def=pack_def, client=Client(url=os.environ['FLYTE_API']))

        loop.run_until_complete(pack.start())
    except KeyboardInterrupt:
        shutdown(loop)
        logger.info('Keyboard exception received. Exiting.')
        exit()
```

## Running Tests

```
make test
```
## Running the example pack

You need to make sure that flyte server and flyte-slack pack are up and running. 
Please check how to run them locally [here](https://github.com/ExpediaGroup/flyte/blob/master/docs/quickstart.md#spin-up-your-local-environment):

```
make run-example
```

You will also need to push an [example flow](example/flow.yaml) to test it. Check how to do it [here](https://github.com/ExpediaGroup/flyte/blob/master/docs/quickstart.md#installing-a-flow)

## Create a docker container

```
make docker-build
```