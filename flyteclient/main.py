import sys
import time
import logging

import requests

from flyteclient.definitions import PackDef, EventDef, CommandDef, CommandHandler
from flyteclient.pack import Event
from flyteclient.client import Client

logger = logging.getLogger(__name__)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)


class RequestOneCommandHandler(CommandHandler):
    """command handler that process requestOne commands"""
    def handle(self, request) -> Event:
        r = requests.get(url="https://api.pagerduty.com/schedules?query=HCOM-CSI-INCIDENT-ROTA",
                         headers={
                             "Accept": "application/vnd.pagerduty+json;version=2",
                             "Authorization": "Token token=ABCDE",
                                  })

        r.raise_for_status()

        logger.info(r.status_code)
        name = r.json()["schedules"][0]["users"][0]["summary"]
        logger.info(name)

        logger.info("message successfully consumed")
        return Event(event="RotaRetrieved", payload=f"{name}")


try:
    pack_def = PackDef(
        name="page-of-duty-pack",
        commands=[
            CommandDef(name="Rota", handler=RequestOneCommandHandler(), output_events=[
                EventDef(name="RotaRetrieved"),
                EventDef(name="Error"),
            ]),
        ],
        help_url="http://github.com/your-repo.git")

    c = Client(timeout=5)

    createdPack = c.create_pack(pack_def)

    while True:
        try:
            action = c.take_action(createdPack)
            if action is not None:
                e = RequestOneCommandHandler().handle(action)
                c.complete_action(action.get_action_complete_url(), e)
            else:
                logger.info("nothing to do for now, going to sleep for 5 seconds")
                time.sleep(5)
        except Exception as e:
            logger.error("something went wrong", e)
            time.sleep(10)

except KeyboardInterrupt:
    logger.info('Keyboard exception received. Exiting.')
    exit()
