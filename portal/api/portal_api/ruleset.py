"""The adopted Code as data: the Board app's ruleset, vendored and pinned.

The portal reads only an adopted, binding ruleset, and only if every file matches
the SHA-256 its manifest records. Rolling to a newly adopted ruleset is a
deliberate change: vendor the new folder, change PINNED_KEY, run the tests.
"""

import functools
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PINNED_KEY = "adopted-v1.0"
_ROOT = Path(__file__).resolve().parent / "rulesets"
# logical name in the manifest → file name
_FILES = {"articles": "articles.json", "uses": "uses.json", "use_matrix": "use-matrix.json",
          "districts": "districts.json", "clocks": "clocks.json"}


class RulesetError(Exception):
    pass


@dataclass
class Ruleset:
    key: str
    adopted_on: date
    uses: list[dict]
    cells: dict[tuple[str, str], dict]
    legend: dict[str, dict]
    clocks: dict[str, dict]
    districts: list[dict]
    definitions: dict[str, dict]
    _nodes: dict[str, dict] = field(repr=False)

    def cite(self, ref: str) -> str:
        """Code text for "8.10.b.1" (Article.Section.subsection.item…). A lead-in such as
        "reviews and approves:" comes with its listed items, so the quote stands alone."""
        parts = ref.split(".")
        if len(parts) < 3:
            raise RulesetError(f"citation {ref!r} needs article.section.subsection")
        art, sec, sub, *path = parts
        nid = f"{self.key}:a{art}.s{sec}.{sub}" + ("." + ".".join(path) if path else "")
        node = self._nodes.get(nid)
        if node is None:
            raise RulesetError(f"citation {ref!r} is not in {self.key}")
        text = node["text"]
        if text.rstrip().endswith(":"):
            depth = nid.count(".") + 1
            items = [n for k, n in self._nodes.items() if k.startswith(nid + ".") and k.count(".") == depth]
            text += "".join(f"\n{n['path'][-1]}. {n['text']}" for n in items)
        return text


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@functools.cache
def _load(key: str, root: Path) -> Ruleset:
    folder = root / key
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("ruleset_key") != key:
        raise RulesetError(f"manifest is for {manifest.get('ruleset_key')!r}, not {key!r}")
    if manifest.get("kind") != "adopted-czc" or manifest.get("status") != "active" or manifest.get("binding") is not True:
        raise RulesetError(f"{key} is not an active, binding, adopted ruleset (binding={manifest.get('binding')!r})")
    data = {}
    for name, filename in _FILES.items():
        path = folder / filename
        if _sha(path) != manifest["content_sha256"].get(name):
            raise RulesetError(f"{name} does not match the manifest's SHA-256")
        data[name] = json.loads(path.read_text())
    matrix = data["use_matrix"]
    return Ruleset(
        key=key,
        adopted_on=date.fromisoformat(manifest["adopted_on"]),
        uses=matrix["uses"],
        cells={(c["district_key"], c["use_key"]): c for c in matrix["cells"]},
        legend={l["code"]: l for l in matrix["legend"]},
        clocks={c["clock_key"]: c for c in data["clocks"]["clocks"]},
        districts=data["districts"]["districts"],
        definitions=data["uses"]["uses"],
        _nodes={n["id"]: n for n in data["articles"]["nodes"]},
    )


def load_ruleset(key: str = PINNED_KEY, root: Path | None = None) -> Ruleset:
    return _load(key, (root or _ROOT).resolve())


def district_key_for(trace_code: str) -> str | None:
    """Traced district code ("D2", "SD-Marine") → use-table district key ("d2", "sd-marine").
    SD-Civic has no district page and no use-table column, so it maps to None."""
    code = trace_code.strip().upper()
    for d in load_ruleset().districts:
        if code.startswith("SD-"):
            if d["code"] == "SD" and d["name"].upper() == code[3:]:
                return d["district_key"]
        elif d["code"] == code:
            return d["district_key"]
    return None
