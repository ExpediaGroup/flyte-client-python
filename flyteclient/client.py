import logging
from typing import Optional

import requests
from flyteclient import pack, definitions

logger = logging.getLogger(__name__)


class Client:
    __BASE_URL = "http://localhost:8080"

    def __init__(self, url=__BASE_URL, timeout=5, insecure_skip_verify=False, version="v1") -> None:
        self.__url = f'{url}/{version}'
        self.__insecure_skip_verify = insecure_skip_verify
        self.__timeout = timeout
        self.__get_api_links()

    def create_pack(self, p: definitions.PackDef) -> pack.Pack:
        """registers pack definition and return packs metadata"""
        commands = [pack.Command(
            name=c.name,
            events=[e.name for e in c.output_events]
        ) for c in p.commands]

        events = [e for c in p.commands for e in c.output_events]
        pack_to_create = pack.Pack(
            name=p.name,
            commands=commands,
            events=[pack.EventDef(name=e.name, help_url=e.help_url) for e in events]
        )
        return self.__register_pack(pack_to_create)

    def post_event(self, p: pack.Pack, e: pack.Event):
        """posts events to the flyte server"""
        response = requests.post(url=p.get_events_url(), timeout=self.__timeout, verify=self.__insecure_skip_verify)
        response.raise_for_status()
        if response.status_code != 202:
            raise Exception(f"event {e} not accepted, response was: {response.status_code}")
        return

    def take_action(self, p: pack.Pack) -> Optional[pack.Action]:
        """Retrieves all the actions pending to be processed by a pack"""
        try:
            take_action_url = p.get_take_action_url()
            response = requests.post(url=take_action_url, timeout=self.__timeout, verify=self.__insecure_skip_verify)
            if response.status_code == 204:
                logger.info(f"no actions available yet")
                return None
            elif response.status_code == 200:
                return pack.Action.from_json(response.content)
            elif response.status_code == 404:
                logger.error(f"resource not found at url {take_action_url}")
                return None
        except requests.exceptions.RequestException as err:
            logger.error(err)
            return None

    def complete_action(self, complete_action_url: str, e: pack.Event):
        """posts the action result to the flyte server"""
        r = requests.post(url=complete_action_url, timeout=self.__timeout, data=e.to_json(),
                          verify=self.__insecure_skip_verify)
        r.raise_for_status()

    def __register_pack(self, p: pack.Pack) -> pack.Pack:
        """registers the pack in flyte server"""
        packs_url = self.__get_packs_url()
        r = requests.post(url=packs_url, timeout=self.__timeout, data=p.to_json(), verify=self.__insecure_skip_verify)
        r.raise_for_status()
        return pack.Pack.from_json(r.content)

    def __get_packs_url(self) -> str:
        """returns the url to register your pack"""
        return self.__find_relative_link(self.links, "pack/listPacks")

    @staticmethod
    def __find_relative_link(links, rel_name: str) -> str:
        """find a link based on its relative name"""
        link = next((link["href"] for link in links if link["rel"].endswith(rel_name)), None)
        if link is None:
            raise ValueError(f"link {rel_name} not found")
        return link

    def __get_api_links(self):
        """retrieves links from the flyte api server that are useful to the client such as packs url and health url
        and so on """
        response = requests.get(url=self.__url, timeout=self.__timeout, verify=self.__insecure_skip_verify)
        response.raise_for_status()
        self.links = response.json()["links"]
