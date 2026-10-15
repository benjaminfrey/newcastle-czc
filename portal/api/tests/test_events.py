import threading

from sqlalchemy import text

from portal_api.events import GENESIS_HASH, append_event, verify_chain


def test_first_event_links_to_genesis(engine):
    with engine.begin() as conn:
        append_event(conn, actor="system", kind="test.one", payload={"n": 1})
        row = conn.execute(text("SELECT prev_hash FROM event")).one()
    assert row.prev_hash == GENESIS_HASH


def test_chain_verifies(engine):
    with engine.begin() as conn:
        for n in range(3):
            append_event(conn, actor="system", kind="test.n", payload={"n": n})
    with engine.connect() as conn:
        assert verify_chain(conn) == (True, None)


def test_tampering_is_detected(engine):
    with engine.begin() as conn:
        for n in range(3):
            append_event(conn, actor="system", kind="test.n", payload={"n": n})
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE event DISABLE TRIGGER event_append_only"))
        conn.execute(text("UPDATE event SET payload_json = :p WHERE seq = 2"), {"p": '{"n":99}'})
        conn.execute(text("ALTER TABLE event ENABLE TRIGGER event_append_only"))
    with engine.connect() as conn:
        assert verify_chain(conn) == (False, 2)


def test_payload_key_order_does_not_change_the_hash(engine):
    with engine.begin() as conn:
        append_event(conn, actor="system", kind="k", payload={"b": 1, "a": 2})
        stored = conn.execute(text("SELECT payload_json FROM event")).scalar()
    assert stored == '{"a":2,"b":1}'


def test_concurrent_appends_keep_one_chain(engine):
    def worker():
        for n in range(20):
            with engine.begin() as conn:
                append_event(conn, actor="system", kind="test.concurrent", payload={"n": n})

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM event")).scalar() == 40
        assert verify_chain(conn) == (True, None)
