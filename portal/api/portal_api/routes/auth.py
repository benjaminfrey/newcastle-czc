from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import Connection

from portal_api import auth
from portal_api.db import transaction
from portal_api.events import append_event
from portal_api.mail import MailError, signin_email

router = APIRouter()


class LinkRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    token: str


@router.post("/api/auth/request-link", status_code=202)
def request_link(body: LinkRequest, request: Request):
    settings = request.app.state.settings
    engine = request.app.state.engine
    email = auth.normalise_email(body.email)
    bucket = auth.rate_bucket(request.client.host if request.client else None)
    limits = auth.Limits(settings.signin_limit_per_email_ip, settings.signin_limit_per_email,
                         settings.signin_limit_per_ip, settings.signin_limit_global)
    token, hashed = auth.new_token()
    # Three short transactions so no connection or lock is held while the relay
    # talks: reserve (counts toward limits, not yet redeemable), send, then mark
    # sent. A link nobody received is never redeemable.
    with engine.begin() as conn:
        token_id = auth.reserve_signin_token(conn, email=email, hashed=hashed, bucket=bucket,
                                             minutes=settings.signin_link_minutes, limits=limits)
    if token_id is None:
        return JSONResponse({"detail": "too_many_requests"}, status_code=429)
    link = f"{settings.public_base_url}/signin/verify#token={token}"
    try:
        request.app.state.mailer.send(signin_email(email, link, settings.signin_link_minutes))
    except MailError:
        with engine.begin() as conn:
            auth.discard_signin_token(conn, token_id)
        return JSONResponse({"detail": "email_unavailable"}, status_code=503)
    with engine.begin() as conn:
        auth.mark_sent(conn, token_id)
        append_event(conn, actor="anonymous", kind="signin.requested",
                     payload={"signin_token_id": token_id})
    return {"status": "sent"}


@router.post("/api/auth/verify")
def verify(body: VerifyRequest, request: Request, response: Response,
           conn: Connection = transaction):
    settings = request.app.state.settings
    applicant = auth.redeem_signin_token(conn, auth.token_hash(body.token))
    if applicant is None:
        return JSONResponse({"detail": "link_invalid"}, status_code=400)
    session_token = auth.create_session(conn, applicant_id=applicant.id, days=settings.session_days)
    append_event(conn, actor=f"applicant:{applicant.id}", kind="signin.verified",
                 payload={"applicant_id": applicant.id})
    response.set_cookie(
        auth.SESSION_COOKIE, session_token,
        max_age=settings.session_days * 86400, path="/",
        httponly=True, secure=settings.cookie_secure, samesite="lax",
    )
    return {"email": applicant.email, "role": applicant.role}


@router.get("/api/me")
def me(applicant: auth.Applicant = auth.require):
    return {"email": applicant.email, "role": applicant.role}


@router.post("/api/auth/sign-out", status_code=204)
def sign_out(request: Request, conn: Connection = transaction):
    token = request.cookies.get(auth.SESSION_COOKIE)
    applicant_id = auth.revoke_session(conn, token) if token else None
    if applicant_id:
        append_event(conn, actor=f"applicant:{applicant_id}", kind="signin.signed_out",
                     payload={"applicant_id": applicant_id})
    response = Response(status_code=204)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return response
