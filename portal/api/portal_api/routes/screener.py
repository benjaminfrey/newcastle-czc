from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from portal_api.forms.definitions import load_definitions
from portal_api.forms.screener import use_groups
from portal_api.ratelimit import lookup_limit
from portal_api.ruleset import load_ruleset

router = APIRouter()


def _not_approved() -> JSONResponse:
    return JSONResponse({"detail": "screener_not_approved"}, status_code=503)


@router.get("/api/screener/uses", dependencies=[Depends(lookup_limit)])
def uses(request: Request):
    ruleset = load_ruleset()
    defs = load_definitions(ruleset)
    # While any entry is a draft, the uses are not offered at all.
    if defs.drafts() and not request.app.state.settings.allow_draft_rules:
        return _not_approved()
    groups, _drafts = use_groups(ruleset, defs)
    return groups
