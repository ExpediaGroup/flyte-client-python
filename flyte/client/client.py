import json
import logging
from typing import Optional

import aiohttp

from flyte.client.errors import FlyteClientError, FlyteRequestError
from flyte.client.classes import Link, Event, Action, Pack, find_url_by_relative_name


class Client:
    """
    Htttp client to interact with flyte server
    """

    __BASE_URL = "http://localhost:8080"

    def __init__(
        self, url=__BASE_URL, timeout=5, insecure_skip_verify=False, version="v1"
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._url = f"{url}/{version}"
        self._insecure_skip_verify = insecure_skip_verify
        self._timeout = timeout
        self._links = None
        self._take_action_url = None
        self._events_url = None

    async def create_pack(self, p: Pack) -> Pack:
        """registers pack definition and return packs metadata
        :param p: pack to register into flyte server
        :return: pack info including hateoas links
        :raises FlyteClientError if there is a client or server error calling flyte server api.
        """
        if self._links is None:
            self._links = await self._get_api_links()

        registered_pack = await self._register_pack(p)

        self._take_action_url = registered_pack.get_take_action_url()
        self._events_url = registered_pack.get_events_url()

        return registered_pack

    async def post_event(self, e: Event):
        """posts events to the flyte server
        :param e: Event to send to flyte server
        :raises FlyteClientError when event is not accepted by flyte server
        :raises FlyteClientError when request fails with a client or server error
        """
        if self._events_url is None:
            raise FlyteClientError(
                f"hateoas links not found. You must register your pack first"
            )

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._insecure_skip_verify)
        ) as session:
            content, status_code = await self._post(
                session, self._events_url, e.to_json()
            )
            self._raise_error(status_code, f"error posting {e} : {content}")

            if status_code != 202:
                raise FlyteClientError(
                    f"event {e} not accepted, response was: {status_code}"
                )

    async def take_action(self) -> Optional[Action]:
        """retrieves all the actions pending to be processed by a pack
        :return: None or Action to be processed.
        :raises FlyteClientError when there is a client or server error in flyte server.
        :raises FlyteClientError when resource not found
        """
        if self._take_action_url is None:
            raise FlyteClientError(
                "hateoas links not found. You must register your pack first"
            )

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._insecure_skip_verify)
        ) as session:
            content, status_code = await self._post(
                session, self._take_action_url, None
            )

            if status_code == 204:
                self._logger.info("no actions available yet")
                return None
            elif status_code == 200:
                return Action.from_json(content)
            elif status_code == 404:
                self._logger.error(f"resource not found at url {self._take_action_url}")
                return None
            else:
                self._raise_error(
                    status_code, f"error taking action - {content} : {status_code}"
                )
                return None

    async def complete_action(self, a: Action, e: Event):
        """posts the action result to the flyte server
        :param a Action to mark as completed
        :param e Event result
        :raise FlyteClientError if complete action call fails
        """
        complete_action_url = a.get_action_complete_url()
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._insecure_skip_verify)
        ) as session:
            content, status_code = await self._post(
                session, complete_action_url, e.to_json()
            )
            self._raise_error(
                status_code, f"error posting action - {content} : {status_code}"
            )

    async def _register_pack(self, p: Pack) -> Pack:
        """registers the pack in flyte server
        :param p Pack to register
        :return Pack registered with additional Hateoas links
        :raise FlyteClientError if there is an error registering our pack to flyte api.
        :raise
        """
        packs_url = self._get_packs_url()
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._insecure_skip_verify)
        ) as session:
            result, status_code = await self._post(session, packs_url, p.to_json())
            self._raise_error(status_code, "unable to register the pack")
            return Pack.from_json(result)

    def _get_packs_url(self) -> str:
        """returns the url to register your pack
        :raise ValueError if there is no url matching the relative name
        """
        return find_url_by_relative_name(self._links, "pack/listPacks")

    async def _fetch(self, session: aiohttp.ClientSession, url) -> (str, int):
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        try:
            async with session.get(url=url, timeout=timeout) as response:
                return await response.text(), response.status
        except Exception as e:
            raise FlyteRequestError(url, e)

    async def _post(self, session: aiohttp.ClientSession, url, data) -> (str, int):
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        try:
            async with session.post(url=url, timeout=timeout, data=data) as response:
                return await response.text(), response.status
        except Exception as e:
            raise FlyteRequestError(url, e)

    async def _get_api_links(self) -> [Link]:
        """retrieves links from the flyte api server that are useful to the client such as packs url and health url
        and so on
        :raise FlyteClientError when there is an error when retrieving api links
        """
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=self._insecure_skip_verify)
        ) as session:
            result, status = await self._fetch(session, self._url)
            self._raise_error(status, "unable to fetch api links")
            links = json.loads(result)["links"]
            return Link.schema().load(links, many=True)

    @staticmethod
    def _raise_error(status_code, message):
        """
        raises a FlyteClientError when we got a none successful response from flyte-api (client errors or server errors)
        :param r: response
        :raises FlyteClientError if there is any client or server error
        """
        if status_code > 399:
            raise FlyteClientError(message)
