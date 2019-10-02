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
