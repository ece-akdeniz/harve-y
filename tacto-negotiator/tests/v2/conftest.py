import copy
import socket

import pytest

from tests.v2.support import read_fixture


def pytest_addoption(parser):
    parser.addoption(
        "--v2-require", action="append", default=[], metavar="MODULE_PREFIX",
        help="Fail instead of xfail for absent V2 modules under this prefix; use 'all' at milestone gates.",
    )


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("V2 specification tests must use injected fake gateways, never network connections")

    # Leave socketpair alone: asyncio uses it for its local wake-up mechanism.
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def p10():
    return copy.deepcopy(read_fixture("p10.json"))


@pytest.fixture
def relationship():
    return copy.deepcopy(read_fixture("relationship.json"))
