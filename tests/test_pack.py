import asyncio
import unittest
from unittest import mock
from unittest.mock import Mock, patch

from aiohttp import web
from aiohttp.test_utils import unittest_run_loop, AioHTTPTestCase

from flyte.client.errors import FlyteClientError
from flyte.client.classes import Event as ClientEvent, Pack as ClientPack, Link, Command as ClientCommand, Action
from flyte.pack.classes import PackDef, Command, EventDef, CommandHandler, Event
from flyte.pack.errors import SendEventError
from flyte.pack.pack import Pack


class Command1Handler(CommandHandler):
    def handle(self, request) -> Event:
        return Event(eventDef=create_event_def("event1"), payload="all good!")


def create_event_def(event_name):
    return EventDef(name=event_name, help_url="http://help.com")


class Command2Handler(CommandHandler):
    def handle(self, request) -> Event:
        return Event(eventDef=create_event_def("event2"), payload="all good!")


def createPackDef() -> PackDef:
    return PackDef(
        name="tests",
        labels={"dev": "tests"},
        help_url="http://test.hcom",
        commands=[
            Command(name="command1", handler=Command1Handler(), help_url="http://test.hcom/command1"),
            Command(name="command2", handler=Command2Handler(), help_url="http://test.hcom/command2")
        ],
        event_defs=[],
    )


def createClientCommand(command_name="command1"):
    return ClientCommand(name=command_name, events=[], links=[
        Link(href=f"http://test.hcom/{command_name}", rel='help')])


async def create_future(result):
    future = asyncio.Future()
    future.set_result(result)
    return future


class TestPackRegistration(AioHTTPTestCase):

    async def get_application(self):
        return web.Application()

    def throw_exception(*args, **kwargs):
        raise FlyteClientError(Exception("whoops"))

    @staticmethod
    def create_event_def():
        return EventDef(name="tests", help_url="http://hcom.test")

    @mock.patch("flyte.pack.pack.Pack._register", side_effect=throw_exception)
    def test_start_retries_after_registration_fails(self, register):
        loop = asyncio.get_event_loop()
        p = Pack(pack_def=createPackDef(), client=Mock())
        with self.assertRaises(FlyteClientError):
            loop.run_until_complete(p.start())

        self.assertEqual(register.call_count, 2)

    @unittest_run_loop
    async def test_send_event_raises_a_send_event_error_when_flyte_client_call_fails(self):
        mock_client = Mock()
        mock_client.post_event.side_effect = FlyteClientError("something happened", Exception("whoops"))
        p = Pack(pack_def=createPackDef(), client=mock_client)

        with self.assertRaises(SendEventError) as cm:
            await p.send_event(Event(
                eventDef=self.create_event_def(),
                payload="helloworld"
            ))

        self.assertRegex('{}'.format(cm.exception), "Failed when sending event .* whoops")

    @unittest_run_loop
    async def test_send_event_successfully_sends_and_event_to_flyte_server(self):
        future = await create_future(None)

        mock_client = Mock()
        mock_client.post_event.return_value = future

        p = Pack(pack_def=createPackDef(), client=mock_client)
        await p.send_event(Event(self.create_event_def(), payload="payload"))

        mock_client.post_event.assert_called_once_with(
            ClientEvent(event="tests", payload="payload")
        )

    @unittest_run_loop
    async def test_registers_and_consume_action(self):
        action = Action(command="command1", input="{}", links=[Link(href="link", rel="actionResult")])

        mock_client = Mock()
        mock_client.take_action.return_value = await create_future(action)

        mock_client.create_pack.return_value = await create_future(ClientPack(name="tests", links=[
            Link(href="http://takeAction.url", rel="takeAction")
        ]))
        mock_client.complete_action.return_value = await create_future(action)

        p = Pack(pack_def=createPackDef(), client=mock_client)

        with patch.object(Pack, 'continue_running') as mock_foo:
            mock_foo.side_effect = [True, True, False, False]
            await p.start()

        mock_client.create_pack.assert_called_once_with(
            ClientPack(name="tests",
                       labels={"dev": "tests"},
                       links=[Link(href="http://test.hcom", rel="help")],
                       commands=[
                           createClientCommand("command1"),
                           createClientCommand("command2"),
                       ])
        )

        mock_client.take_action.assert_called_once()
        mock_client.complete_action.assert_called_once_with(action,
                                                            ClientEvent(event="event1", payload="all good!"))


if __name__ == '__main__':
    unittest.main()
