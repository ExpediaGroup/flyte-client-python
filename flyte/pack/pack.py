import asyncio
import logging
import time
from typing import Dict

from flyte.client.client import Client
from flyte.client.errors import FlyteClientError
from flyte.client.classes import Action as ClientAction
from flyte.pack.classes import PackDef, Event, CommandHandler, fatal_event
from flyte.pack.errors import SendEventError
from flyte.pack.health import HealthCheck
from flyte.pack.mappers import to_client_pack, to_client_event

register_retry_wait_in_seconds = 3


class Pack:
    def __init__(
        self,
        pack_def: PackDef,
        client: Client,
        health_checks: HealthCheck = [],
        polling_frequency_in_seconds=5,
    ) -> None:
        self._polling_frequency_in_seconds = polling_frequency_in_seconds
        self._health_checks = health_checks
        self._client = client
        self._pack_def = pack_def
        self._logger = logging.getLogger(__name__)
        self._registration = None

    async def start(self):
        """Registers the pack with the flyte server and starts handling actions from the flyte server and invoking
        the necessary commands. Once started the Pack is also available to send observed events. // This will also
        start up a pack health check server. """
        try:
            await self._register()
            self._logger.info(f"pack {self._pack_def.name} registered successfully")
        except FlyteClientError:
            time.sleep(register_retry_wait_in_seconds)
            await self._register()
            self._logger.info(f"pack {self._pack_def.name} registered successfully")
            return

        await asyncio.gather(self._handle_commands(), self._start_health_check_server())

    async def send_event(self, event: Event):
        """Spontaneously sends an event that the pack has observed to the flyte server
        :param event Event to be sent to flyte server"""
        try:
            await self._client.post_event(to_client_event(event))
        except FlyteClientError as e:
            self._logger.error("failed to send the event", e)
            raise SendEventError(event, e)

    async def _register(self):
        """Registers this pack to Flyte.
        """
        self._pack = await self._client.create_pack(to_client_pack(self._pack_def))

    async def _handle_commands(self):
        """repeatedly takes the next incoming action from the flyte server, passes to the appropriate handler and
        sends the output event to the flyte server """
        if len(self._pack_def.commands) > 0:
            await self._handle_command_actions()

    async def _start_health_check_server(self):
        pass

    async def _handle_command_actions(self):
        """
        delegates the execution of an action to a handler
        :return: None
        """
        handlers = {c.name: c.handler for c in self._pack_def.commands}
        while self.continue_running():
            action = await self._get_next_action()
            await self._handle_action(handlers, action)

    async def _get_next_action(self) -> ClientAction:
        """
        fetches new actions from flyte server
        :return:
        """
        while self.continue_running():
            try:
                action = await self._client.take_action()
            except FlyteClientError as err:
                self._logger.error("there was an error fetching actions", err)
                action = None

            if action is not None:
                return action
            else:
                time.sleep(self._polling_frequency_in_seconds)

    async def _handle_action(
        self, handlers: Dict[str, CommandHandler], action: ClientAction
    ):
        """
        executes the handler associated to a specific command and completes the action
        :param handlers: handlers associated to a command
        :param action: action to be processed
        :return:
        """
        if action is None:
            return

        if action.command in handlers:
            output_event = handlers[action.command].handle(action.input)
            await self._complete_action(action, output_event)
        else:
            self._logger.error(
                f"no handler could be found for command {action.command} in {handlers}"
            )
            await self._complete_action(
                action,
                fatal_event(
                    f"no handler could be found for command {action.command} in {handlers}"
                ),
            )

    @staticmethod
    def continue_running() -> bool:
        """
        method used to control the flow of our app. Only useful during testing.
        :return: True
        """
        return True

    async def _complete_action(self, action: ClientAction, event: Event):
        """
        mark an action as completed in flyte server
        :param action: action to be marked as completed
        :param event: result
        :return:
        """
        try:
            await self._client.complete_action(action, to_client_event(event))
        except FlyteClientError as err:
            self._logger.error("could not complete action %s: %s", action, err)
