from portal_api.guide.drawing import roles
from tests.test_guide_routes import answer, front, started, walk  # noqa: F401
from tests.test_projects import alice, app, bob, create  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

ROAD = {"name": "Sheepscot Road", "type": "R2"}


def _square(south=ROAD, north=None):
    """A 100 ft square, clockwise from its south-west corner (y north)."""
    return [
        {"id": "L1", "points": [[-50, -50], [-50, 50]], "street": None},     # west
        {"id": "L2", "points": [[-50, 50], [50, 50]], "street": north},      # north
        {"id": "L3", "points": [[50, 50], [50, -50]], "street": None},       # east
        {"id": "L4", "points": [[50, -50], [-50, -50]], "street": south},    # south
    ]


def test_rectangle_roles():
    assert roles(_square(), "L4") == {"L4": "front", "L2": "rear", "L1": "side", "L3": "side"}


def test_a_second_road_line_is_a_frontage_not_a_rear():
    r = roles(_square(north={"name": "River Road", "type": "R2"}), "L4")
    assert r == {"L4": "front", "L2": "frontage", "L1": "side", "L3": "side"}


def test_no_roles_until_the_front_is_chosen():
    assert roles(_square(), None) is None
    assert roles(_square(), "other") is None
    assert roles(_square(), "L9") is None


def test_a_rear_must_be_roughly_opposite_the_front():
    """A triangle: no line is within 60° of opposite the front, so there is no rear."""
    tri = [{"id": "L1", "points": [[-50, -50], [0, 50]], "street": None},
           {"id": "L2", "points": [[0, 50], [50, -50]], "street": None},
           {"id": "L3", "points": [[50, -50], [-50, -50]], "street": ROAD}]
    assert roles(tri, "L3") == {"L3": "front", "L1": "side", "L2": "side"}


def _drawing(client, pid):
    return client.get(f"/api/projects/{pid}/guide/drawing")


def test_drawing_route_returns_outline_roles_and_limits(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes")])
    body = _drawing(alice, pid).json()
    assert body["outline"]["approximate"] is True and len(body["outline"]["lines"]) == 4
    road = next(L["id"] for L in body["outline"]["lines"] if L["street"])
    assert body["front"] == road and body["roles"][road] == "front"
    # The fixture lot is 75% D2 and 25% D1: both ask 20 ft at the front, and they disagree at the side.
    assert body["limits"]["front"]["min"] == 20 and body["limits"]["front"]["reason"] is None
    assert body["limits"]["side"]["min"] is None and body["limits"]["side"]["reason"] == "two_districts"
    assert set(body["limits"]) == {"front", "side", "rear"}


def test_no_roles_before_the_front_is_answered(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes")])
    body = _drawing(alice, pid).json()
    assert body["outline"] is not None and body["front"] is None and body["roles"] is None


def test_drawing_is_null_without_an_outline(alice):
    pid = create(alice, ("building",), prop={"source": "manual", "map_lot": "4-36", "district_code": "D1"})
    r = alice.post(f"/api/projects/{pid}/guide", json={"opening": "new_house", "base_revision": 0})
    assert r.status_code == 201, r.text
    r = _drawing(alice, pid)
    assert r.status_code == 200 and r.json()["outline"] is None and r.json()["roles"] is None


def test_someone_elses_drawing_is_404(alice, bob):
    pid = started(alice)
    assert _drawing(bob, pid).status_code == 404
