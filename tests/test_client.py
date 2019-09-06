import unittest
from unittest import mock
from unittest.mock import patch

import requests
from requests import HTTPError

from flyteclient.client import Client
from flyteclient.definitions import PackDef, CommandDef, EventDef
from flyteclient.pack import Link


class MyTestCase(unittest.TestCase):

    @staticmethod
    def _mock_response(
            status=200,
            content="CONTENT",
            json_data=None,
            raise_for_status=None):
        mock_resp = mock.Mock()
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        mock_resp.status_code = status
        mock_resp.content = content
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    @patch("requests.get")
    def test_fails_when_fetching_hateoas_links_fails(self, requests_get):
        mock_resp = self._mock_response(status=500, raise_for_status=HTTPError("api is down"))
        requests_get.return_value = mock_resp

        self.assertRaises(requests.exceptions.HTTPError, Client)

    @patch("requests.get")
    def test_successfully_returns_flyte_api_links(self, requests_get):
        requests_get.return_value = self._mock_response(status=200, json_data={"links": []})

        Client(url="http://unitest")

        requests_get.assert_called_with(url="http://unitest/v1", timeout=5, verify=False)

    @patch("requests.get")
    def test_fails_when_client_cant_find_list_pack_link(self, requests_get):
        requests_get.return_value = self._mock_response(status=200, json_data={
            "links": [
                {
                    "href": "http://unitest/v1/packs",
                    "rel": "something"
                }
            ]
        })

        c = Client()

        self.assertRaises(ValueError, c.create_pack, PackDef(name="test", commands=[], help_url=""))

    @patch("requests.get")
    @patch("requests.post")
    def test_fails_when_client_cant_register_a_pack(self, requests_post, requests_get):
        requests_get.return_value = self._mock_response(status=200, json_data=self.get_hateoas_links())
        requests_post.return_value = self._mock_response(status=500, raise_for_status=HTTPError("invalid data"))

        c = Client()

        self.assertRaises(requests.exceptions.HTTPError, c.create_pack, PackDef(name="test", commands=[], help_url=""))

    @patch("requests.get")
    @patch("requests.post")
    def test_successfully_registers_a_pack(self, requests_post, requests_get):
        requests_get.return_value = self._mock_response(status=200, json_data=self.get_hateoas_links())
        requests_post.return_value = self._mock_response(status=200, content="""{
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
                }
            ]
        }""")

        c = Client(url="http://unitest")
        pack_def = PackDef(name="FakeSlack",
                           commands=[
                               CommandDef(name="SendMessage",
                                          handler=None,
                                          help_url="http://unitest/command/help",
                                          output_events=[
                                              EventDef(name="MessageReceived"),
                                              EventDef(name="SendMessageFailed"),
                                          ])
                           ],
                           help_url="http://unitest/help")
        pack = c.create_pack(pack_def)

        requests_get.assert_called_with(url="http://unitest/v1", timeout=5, verify=False)

        self.assertEqual(pack.name, "FakeSlack")
        self.assertEqual(pack.commands[0].name, "SendMessage")
        self.assertCountEqual(["MessageSent", "SendMessageFailed", "MessageReceived"],
                              [e for e in pack.commands[0].events])
        self.assertCountEqual(["MessageSent", "SendMessageFailed", "MessageReceived"],
                              [e.name for e in pack.events])

        null = None

        self.assertEqual(Link(href="http://unitest/v1/packs/FakeSlack", rel="self"), pack.links[0])
        requests_post.assert_called_with(url="http://unitest/v1/packs", timeout=5, data={
            "name": "FakeSlack",
            "links": [],
            "commands": [
                {"name": "SendMessage", "events": ["MessageReceived", "SendMessageFailed"]}
            ],
            "events": [
                {"name": "MessageReceived", "helpUrl": null},
                {"name": "SendMessageFailed", "helpUrl": null}
            ]
        }, verify=False)

    @staticmethod
    def get_hateoas_links():
        return {
            "links": [
                {
                    "href": "http://unitest/v1/packs",
                    "rel": "http://unitest/swagger#!/pack/listPacks"
                }
            ]
        }


if __name__ == '__main__':
    unittest.main()
