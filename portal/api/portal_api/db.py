from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy import Connection, Engine, create_engine


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def get_conn(request: Request) -> Iterator[Connection]:
    """One transaction per request: committed on success, rolled back on error."""
    with request.app.state.engine.begin() as conn:
        yield conn


# Use this, not Depends(get_conn): with FastAPI's default "request" scope the
# commit happens *after* the response is sent, so a client could act on a 200
# whose writes are not yet (or never) committed. "function" scope commits first.
transaction = Depends(get_conn, scope="function")
