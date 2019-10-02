import asyncio
import unittest

from aiohttp import web

from flyte import Client, Pack
from flyte.pack.classes import PackDef, Command, CommandHandler, Event, EventDef


class RequestOneCommandHandler(CommandHandler):
    """command handler that process requestOne commands"""

    def handle(self, request) -> Event:
        return Event(eventDef=EventDef(name="RotaRetrieved"), payload="Isaac")


class TestWebClientFunctional(unittest.TestCase):
    def setUp(self):
        self.register_pack_called = False
        self.take_action_called = False
        self.complete_action_called = False

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        task = asyncio.ensure_future(self.mock_server(), loop=self.loop)
        self.loop.run_until_complete(asyncio.wait_for(task, 0.1))

    def tearDown(self):
        self.loop.run_until_complete(self.site.stop())

    async def mock_server(self):
        app = web.Application()
        app.router.add_get("/v1", self.links)
        app.router.add_post("/v1/packs", self.register)
        app.router.add_post("/v1/packs/page-of-duty-pack/actions/take", self.take)
        app.router.add_post("/v1/packs/page-of-duty-pack/actions/id/result", self.complete)
        runner = web.AppRunner(app)
        await runner.setup()
        self.site = web.TCPSite(runner, "localhost", 8765)
        await self.site.start()

    async def links(self, _):
        return web.json_response({"links": [
            {
                "href": f"{self.site.name}/v1/packs",
                "rel": f"{self.site.name}/swagger#!/pack/listPacks"
            }
        ]})

    async def complete(self, _):
        self.complete_action_called = True
        return web.json_response({"result": "ok"})

    async def take(self, _):
        self.take_action_called = True
        return web.json_response({
            "command": "Rota",
            "input": "tests",
            "links": [
                {
                    "href": f"{self.site.name}/v1/packs/page-of-duty-pack/actions/id/result",
                    "rel": f"{self.site.name}/swagger#!/action/actionResult"
                }
            ]})

    async def register(self, _):
        self.register_pack_called = True
        return web.json_response({
            "id": "page-of-duty-pack",
            "name": "page-of-duty-pack",
            "commands": [
                {
                    "name": "Rota",
                    "events": [
                        "RotaRetrieved",
                        "Error"
                    ]
                }
            ],
            "events": [
                {
                    "name": "RotaRetrieved"
                }
            ],
            "links": [
                {
                    "href": f"{self.site.name}/v1/packs/page-of-duty-pack/actions/take",
                    "rel": f"{self.site.name}/swagger#!/action/takeAction"
                },
                {
                    "href": f"{self.site.name}/v1/packs/page-of-duty-pack/events",
                    "rel": f"{self.site.name}/swagger#/event"
                }
            ]
        })

    def test_registration_take_action_and_complete_action(self):
        pack_def = PackDef(
            name="page-of-duty-pack",
            commands=[
                Command(name="Rota", handler=RequestOneCommandHandler(), output_events=[
                    EventDef(name="RotaRetrieved"),
                    EventDef(name="Error"),
                ]),
            ],
            labels={},
            event_defs=[],
            help_url="http://github.com/your-repo.git")

        self.pack = Pack(pack_def=pack_def,
                         client=Client(url=self.site.name))

        def patch_continue_running(that):
            def all_flow_processed():
                return not (that.register_pack_called and that.take_action_called and that.complete_action_called)

            return all_flow_processed

        self.pack.continue_running = patch_continue_running(self)

        self.loop.run_until_complete(self.pack.start())


if __name__ == '__main__':
    unittest.main()
