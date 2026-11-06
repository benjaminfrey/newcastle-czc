from portal_api.guide.drawing import frontages, roles
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


ALLEY = {"name": "Back Alley", "type": "S5"}
STREET = {"name": "Main Street", "type": "S2"}


def test_an_alley_line_is_never_a_frontage_and_may_be_the_rear():
    """Article 9: buildings do not front on an Alley (S5); Article 2: a road frontage may not be a
    rear lot line, "except an alley" (chair, 2026-11-05)."""
    assert roles(_square(north=ALLEY), "L4") == {"L4": "front", "L2": "rear", "L1": "side", "L3": "side"}
    assert frontages(_square(north=ALLEY)) == {"kind": "one", "primary": "L4", "secondary": []}


def test_one_road_line_is_the_front():
    assert frontages(_square()) == {"kind": "one", "primary": "L4", "secondary": []}
    assert frontages(_square(south=None)) == {"kind": "none", "primary": None, "secondary": []}


def _corner(west, south):
    sq = _square(south=south)
    sq[0] = {**sq[0], "street": west}
    return sq


def test_a_corner_lot_fronts_on_the_road_of_the_highest_type():
    """Article 2: Streets take precedence over Roads; within a family the lower code wins. The
    chair applies that rule, written for new lots, to existing ones (2026-11-05)."""
    assert frontages(_corner(STREET, ROAD)) == {"kind": "corner", "primary": "L1", "secondary": ["L4"]}
    r1 = {"name": "River Road", "type": "R1"}
    assert frontages(_corner(ROAD, r1)) == {"kind": "corner", "primary": "L4", "secondary": ["L1"]}


def test_a_corner_on_two_roads_of_one_type_goes_to_the_town():
    assert frontages(_corner({"name": "River Road", "type": "R2"}, ROAD))["kind"] == "town"


def test_a_through_lot_goes_to_the_town():
    """Roads on opposite sides: Article 9 defines a secondary frontage only on corner lots."""
    assert frontages(_square(north=STREET))["kind"] == "town"


def test_a_road_with_no_type_goes_to_the_town():
    assert frontages(_corner({"name": "Unnamed", "type": None}, ROAD))["kind"] == "town"


def test_an_alley_does_not_make_a_corner():
    assert frontages(_corner(ALLEY, ROAD)) == {"kind": "one", "primary": "L4", "secondary": []}


def test_a_corner_lots_other_road_is_its_secondary_frontage():
    assert roles(_corner(STREET, ROAD), "L1") == {"L1": "front", "L4": "secondary", "L3": "rear", "L2": "side"}


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
    assert set(body["limits"]) == {"front", "side", "rear", "secondary"}
    # The secondary front setback, for a corner lot's other road: 20 ft in both D2 and D1.
    assert body["limits"]["secondary"]["min"] == 20


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
