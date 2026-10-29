"""The screener's rules, run as `POST /api/screener` ran them before projects (projects brief
§5.4 removed the route; the rules now run inside `GET /api/projects/{id}`). The rule tests
keep their shape: `runner.post("/api/screener", json=answers)` gives a response-like object."""

from dataclasses import dataclass

from pydantic import ValidationError

from portal_api.forms.definitions import load_definitions
from portal_api.forms.screener import Answers, run
from portal_api.ruleset import load_ruleset


@dataclass
class Result:
    status_code: int
    body: dict

    def json(self):
        return self.body

    @property
    def text(self):
        return str(self.body)


class Runner:
    def __init__(self, client=None):
        self._client = client

    def post(self, path: str, json: dict) -> Result:
        assert path == "/api/screener", path
        ruleset = load_ruleset()
        try:
            answers = Answers.model_validate(json)
        except ValidationError:
            return Result(422, {"detail": "invalid"})
        if answers.use_key is not None and answers.use_key not in {u["use_key"] for u in ruleset.uses}:
            return Result(422, {"detail": "unknown_use"})
        return Result(200, run(answers.model_dump(), ruleset, load_definitions(ruleset)))

    def get(self, path: str):
        return self._client.get(path)
