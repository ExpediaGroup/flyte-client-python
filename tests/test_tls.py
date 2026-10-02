import asyncio
import ssl

import pytest
import trustme
from aiohttp import web

from flyte.client.client import Client
from flyte.client.errors import FlyteRequestError


@pytest.mark.parametrize("insecure_skip_verify", [False, True])
def test_https_certificate_verification(insecure_skip_verify):
    async def run():
        certificate = trustme.CA().issue_cert("127.0.0.1")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        certificate.configure_cert(context)
        application = web.Application()

        async def links(request):
            return web.json_response({"links": []})

        application.router.add_get("/v1", links)
        runner = web.AppRunner(application)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0, ssl_context=context)
        await site.start()
        try:
            port = runner.addresses[0][1]
            client = Client(
                url="https://127.0.0.1:{}".format(port),
                insecure_skip_verify=insecure_skip_verify,
            )
            if insecure_skip_verify:
                assert await client._get_api_links() == []
            else:
                with pytest.raises(FlyteRequestError):
                    await client._get_api_links()
        finally:
            await runner.cleanup()

    asyncio.run(run())
