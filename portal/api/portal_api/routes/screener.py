from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from portal_api.forms.definitions import load_definitions
from portal_api.forms.screener import Answers, run, use_groups
from portal_api.ratelimit import lookup_limit
from portal_api.ruleset import load_ruleset

router = APIRouter()


def _not_approved() -> JSONResponse:
    return JSONResponse({"detail": "screener_not_approved"}, status_code=503)


@router.post("/api/screener", dependencies=[Depends(lookup_limit)])
def screener(answers: Answers, request: Request):
    ruleset = load_ruleset()
    defs = load_definitions(ruleset)
    if answers.use_key is not None and answers.use_key not in {u["use_key"] for u in ruleset.uses}:
        raise HTTPException(status_code=422, detail="unknown_use")
    # Refuse while ANY entry is a draft, not only those an answer used: an answer where
    # nothing applied ("the Code calls for nothing") rests on the drafts just as much.
    if defs.drafts() and not request.app.state.settings.allow_draft_rules:
        return _not_approved()
    return run(answers.model_dump(), ruleset, defs)


@router.get("/api/screener/uses", dependencies=[Depends(lookup_limit)])
def uses(request: Request):
    ruleset = load_ruleset()
    groups, drafts = use_groups(ruleset, load_definitions(ruleset))
    if drafts and not request.app.state.settings.allow_draft_rules:
        return _not_approved()
    return groups
