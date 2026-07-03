import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


_exit_stack: Optional[AsyncExitStack] = None
_session: Optional[ClientSession] = None


# command=sys.executable ensures the child uses this venv's interpreter (matters on Windows,
# where a bare "python" may resolve to a different install).
# env=os.environ.copy() is critical: StdioServerParameters does NOT forward the full parent
# environment by default, so without this the spawned server never sees OPENAI_API_KEY
# (loaded via load_dotenv() in the parent) and every tool call would fail auth.
SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["-m", "app.mcp_server.server"],
    env=os.environ.copy(),
)


async def get_mcp_session() -> ClientSession:
    """
    Lazily starts the MCP server subprocess and returns a cached, persistent
    ClientSession that lives for the lifetime of the app.
    """

    global _exit_stack, _session

    if _session is not None:
        return _session

    _exit_stack = AsyncExitStack()
    read, write = await _exit_stack.enter_async_context(stdio_client(SERVER_PARAMS))
    session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()

    _session = session
    return _session


async def close_mcp_session() -> None:
    """
    Terminates the MCP server subprocess and releases resources.
    Safe to call even if the session was never started.
    """

    global _exit_stack, _session

    if _exit_stack is not None:
        await _exit_stack.aclose()

    _exit_stack = None
    _session = None
