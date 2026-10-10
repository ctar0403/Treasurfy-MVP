from __future__ import annotations

import asyncio

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy_cloudflare_d1 import create_engine_from_binding
from workers import WorkerEntrypoint, asgi

from treasurfy.config import Settings
from treasurfy.database import Database
from treasurfy.main import create_app
from treasurfy.seed import seed_demo_data


app = create_app(
    Settings(database_url="cloudflare-d1://", seed_demo=True),
    initialize_database=False,
    defer_database=True,
)
_database_lock = asyncio.Lock()
_database_ready = False


async def initialize_database(binding) -> None:
    global _database_ready
    if _database_ready:
        return

    async with _database_lock:
        if _database_ready:
            return
        database = Database(create_engine_from_binding(binding))
        database.create_schema()
        with database.session_factory() as session:
            seed_demo_data(session)
        app.state.database = database
        _database_ready = True


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str, request: Request) -> Response:
    if path == "api" or path.startswith("api/"):
        return Response(status_code=404)

    env = request.scope["env"]
    requested_asset = path or "index.html"
    asset_response = await env.ASSETS.fetch(f"https://assets.local/{requested_asset}")
    if asset_response.status == 404 and "." not in requested_asset.rsplit("/", 1)[-1]:
        asset_response = await env.ASSETS.fetch("https://assets.local/index.html")
    return Response(
        content=await asset_response.bytes(),
        status_code=asset_response.status,
        headers=dict(asset_response.headers),
    )


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        await initialize_database(self.env.DB)
        return await asgi.fetch(app, request, self.env)
