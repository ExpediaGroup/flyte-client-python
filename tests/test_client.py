import unittest
from unittest.mock import patch

from aiohttp import web, ClientTimeout
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from asynctest import patch, CoroutineMock

from flyte.client.client import Client
from flyte.client.errors import FlyteClientError
from flyte.client.classes import Pack, Link, Command, Event, Action


def set_mock_response(mock_get, status, content=None):
    mock_get.return_value.__aenter__.return_value.status = status
    mock_get.return_value.__aenter__.return_value.text = CoroutineMock(return_value=content)


class ClientTestCase(AioHTTPTestCase):
    timeout = ClientTimeout(total=5, connect=None, sock_read=None, sock_connect=None)

    async def get_application(self):
        return web.Application()

    @unittest_run_loop
    @patch('aiohttp.ClientSession.get')
    async def test_create_pack_fails_when_client_cant_fetch_api_links(self, mock_get):
        set_mock_response(mock_get, 500)

        c = Client()

        with self.assertRaises(FlyteClientError) as cm:
            await c.create_pack(Pack(name="tests", commands=[], links=[]))

        self.assertEqual("unable to fetch api links", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.get')
    async def test_create_pack_fails_when_timeout(self, mock_get):
        mock_get.side_effect = CoroutineMock(side_effect=ClientTimeout())

        c = Client(url="http://test/unit")

        with self.assertRaises(FlyteClientError) as cm:
            await c.create_pack(Pack(name="tests", commands=[], links=[]))

        self.assertEqual("failed when calling http://test/unit/v1: __aexit__", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.get')
    async def test_create_pack_fails_when_client_cant_find_list_pack_link(self, mock_get):
        set_mock_response(mock_get, 500)
        set_mock_response(mock_get, 200, content="""{
            "links": [
                {
                    "href": "http://unitest/v1/packs",
                    "rel": "something"
                }
            ]
        }""")

        c = Client()

        with self.assertRaises(ValueError) as _:
            await c.create_pack(Pack(name="tests", commands=[], links=[]))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    @patch('aiohttp.ClientSession.get')
    async def test_create_pack_returns_flyte_client_error_when_flyte_server_fails(self, mock_get, mock_post):
        set_mock_response(mock_get, 200, content=self.get_hateoas_links())
        set_mock_response(mock_post, 500)

        c = Client()

        with self.assertRaises(FlyteClientError) as cm:
            await c.create_pack(Pack(name="tests", commands=[], links=[]))

        self.assertEqual("unable to register the pack", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    @patch('aiohttp.ClientSession.get')
    async def test_create_pack_returns_flyte_client_error_when_flyte_server_timesout(self, mock_get, mock_post):
        set_mock_response(mock_get, 200, content=self.get_hateoas_links())
        mock_post.side_effect = CoroutineMock(side_effect=ClientTimeout())

        c = Client(url="http://unittest")

        with self.assertRaises(FlyteClientError) as cm:
            await c.create_pack(Pack(name="tests", commands=[], links=[]))

        self.assertEqual("failed when calling http://unitest/v1/packs: __aexit__", '{}'.format(cm.exception))

    @unittest_run_loop
    async def test_create_pack_successfully_registers_a_pack(self):
        _, pack_registered, c = await self.register_pack()

        self.assertEqual(pack_registered.name, "FakeSlack")
        self.assertEqual(pack_registered.commands[0].name, "SendMessage")
        self.assertCountEqual(["MessageSent", "SendMessageFailed", "MessageReceived"],
                              [e for e in pack_registered.commands[0].events])
        self.assertCountEqual(["MessageSent", "SendMessageFailed", "MessageReceived"],
                              [e.name for e in pack_registered.events])

        self.assertEqual(Link(href="http://unitest/v1/packs/FakeSlack", rel="self"), pack_registered.links[0])

    @unittest_run_loop
    async def test_post_event_fails_when_pack_has_not_been_registered_yet(self):
        c = Client()

        with self.assertRaises(FlyteClientError) as cm:
            await c.post_event(Event(event="tests", payload="tests"))

        self.assertEqual("hateoas links not found. You must register your pack first", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_post_event_returns_flyte_client_error_when_flyte_server_fails(self, mock_post):
        set_mock_response(mock_post, 500)

        _, _, c = await self.register_pack()

        with self.assertRaises(FlyteClientError) as cm:
            await c.post_event(Event(event="tests", payload="tests"))

        self.assertEqual("error posting Event(event='tests', payload='tests') : None", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_post_event_successfully_sends_an_event_to_flyte_server(self, mock_post):
        set_mock_response(mock_post, 202, content="accepted")

        _, _, c = await self.register_pack()

        event = Event(event="tests", payload="tests")
        await c.post_event(event)

        mock_post.assert_called_with(url="http://unitest/v1/packs/FakeSlack/event",
                                     timeout=self.timeout,
                                     data=event.to_json())

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_post_event_returns_flyte_client_error_when_flyte_does_not_accept_the_event(self, mock_post):
        set_mock_response(mock_post, 200, content="ok")

        _, _, c = await self.register_pack()
        with self.assertRaises(FlyteClientError) as cm:
            await c.post_event(Event(event="tests", payload="tests"))

        self.assertRegex('{}'.format(cm.exception), "event .* not accepted, response was: 200")

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_take_action_returns_no_action_when(self, mock_post):
        tests = (
            ("nothing to process", 204),
            ("resource not found", 404),
            ("unexpected http status code", 302),
        )

        _, _, c = await self.register_pack()

        for message, error in tests:
            set_mock_response(mock_post, error)
            action = await c.take_action()
            self.assertIsNone(action, message)

    @unittest_run_loop
    async def test_take_action_fails_when__pack_has_not_been_registered_yet(self):
        c = Client()

        with self.assertRaises(FlyteClientError) as cm:
            await c.take_action()

        self.assertEqual("hateoas links not found. You must register your pack first", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_take_action_returns_flyte_client_error_when_flyte_server_fails(self, mock_post):
        _, _, c = await self.register_pack()

        set_mock_response(mock_post, 500, content="server error")

        with self.assertRaises(FlyteClientError) as cm:
            await c.take_action()

        self.assertEqual("error taking action - server error : 500", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_take_action_returns_an_action_to_process(self, mock_post):
        _, _, c = await self.register_pack()

        set_mock_response(mock_post, 200, content="""{
            "command": "command1",
            "input": "input",
            "links": [{"href":"event.link", "rel":"help"}]
        }""")

        action = await c.take_action()

        mock_post.assert_called_with(url="http://unitest/v1/packs/FakeSlack/takeAction",
                                     data=None,
                                     timeout=self.timeout)
        self.assertEqual(action, Action(command="command1", input="input", links=[
            Link(href="event.link", rel="help")
        ]))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_complete_action_returns_flyte_client_error_when_flyte_server_fails(self, mock_post):
        _, _, c = await self.register_pack()

        set_mock_response(mock_post, 500, content="server error")
        action = Action(command="command",
                        input="result",
                        links=[Link(href="http://actionResult", rel="actionResult")])
        event = Event(event="ok", payload="all_good")

        with self.assertRaises(FlyteClientError) as cm:
            await c.complete_action(action, event)

        self.assertEqual("error posting action - server error : 500", '{}'.format(cm.exception))

    @unittest_run_loop
    @patch('aiohttp.ClientSession.post')
    async def test_complete_action_successfully_completes_an_action(self, mock_post):
        _, _, c = await self.register_pack()
        set_mock_response(mock_post, 200)

        action = Action(command="command",
                        input="result",
                        links=[Link(href="http://complete.action.url", rel="actionResult")])
        event = Event(event="ok", payload="all_good")

        await c.complete_action(action, event)

        mock_post.assert_called_with(url="http://complete.action.url",
                                     timeout=self.timeout,
                                     data=event.to_json())

    @staticmethod
    def get_hateoas_links() -> str:
        return """{
            "links": [
                {
                    "href": "http://unitest/v1/packs",
                    "rel": "http://unitest/swagger#!/pack/listPacks"
                }
            ]
        }"""

    async def register_pack(self):
        with patch('aiohttp.ClientSession.get') as mock_get:
            set_mock_response(mock_get, 200, content=self.get_hateoas_links())
            with patch('aiohttp.ClientSession.post') as mock_post:
                set_mock_response(mock_post, 200, content="""{
                    "name": "FakeSlack",
                    "commands": [
                        {
                            "name": "SendMessage",
                            "events": [
                                "MessageReceived",
                                "SendMessageFailed",
                                "MessageSent"
                            ],
                            "links": [
                                {
                                    "href": "http://unitest/v1/packs/FakeSlack/actions/take?commandName=SendMessage",
                                    "rel": "http://unitest/swagger#!/action/takeAction"
                                }
                            ]
                        }
                    ],
                    "events": [
                        {
                            "name": "MessageSent"
                        },
                        {
                            "name": "SendMessageFailed"
                        },
                        {
                            "name": "MessageReceived"
                        }
                    ],
                    "links": [
                        {
                            "href": "http://unitest/v1/packs/FakeSlack",
                            "rel": "self"
                        },
                        {
                            "href": "http://unitest/v1/packs/FakeSlack/event",
                            "rel": "event"
                        },
                        {
                            "href": "http://unitest/v1/packs/FakeSlack/takeAction",
                            "rel": "takeAction"
                        }
                    ]
                }""")
                pack = Pack(name="FakeSlack",
                            commands=[
                                Command(name="SendMessage",
                                        links=[Link(href="http://unitest/command/help", rel="help")],
                                        events=["MessageReceived", "SendMessageFailed"]),
                            ],
                            links=[Link(href="http://unitest/help", rel="help")])

                c = Client(url="http://unitest")
                pack_registered = await c.create_pack(pack)

                mock_get.assert_called_with(url="http://unitest/v1", timeout=self.timeout)
                mock_post.assert_called_with(url="http://unitest/v1/packs", timeout=self.timeout, data=pack.to_json())
        return pack, pack_registered, c


if __name__ == '__main__':
    unittest.main()
