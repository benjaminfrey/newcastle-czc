from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import Connection

from portal_api import auth
from portal_api.db import get_conn
from portal_api.events import append_event
from portal_api.mail import MailError, signin_email

router = APIRouter()


class LinkRequest(BaseModel):
    email: EmailStr


class VerifyRequest(BaseModel):
    token: str


@router.post("/api/auth/request-link", status_code=202)
def request_link(body: LinkRequest, request: Request, conn: Connection = Depends(get_conn)):
    settings = request.app.state.settings
    email = auth.normalise_email(body.email)
    ip = request.client.host if request.client else None
    applicant_id = auth.upsert_applicant(conn, email)
    by_email, by_ip = auth.recent_requests(conn, applicant_id=applicant_id, ip=ip)
    if by_email >= settings.signin_limit_per_email or by_ip >= settings.signin_limit_per_ip:
        return JSONResponse({"detail": "too_many_requests"}, status_code=429)
    token, hashed = auth.new_token()
    link = f"{settings.public_base_url}/signin/verify#token={token}"
    # Send first, store second: a link nobody received is never redeemable. If the
    # store fails after a successful send, the emailed link is simply dead.
    try:
        request.app.state.mailer.send(signin_email(email, link, settings.signin_link_minutes))
    except MailError:
        return JSONResponse({"detail": "email_unavailable"}, status_code=503)
    auth.store_signin_token(conn, applicant_id=applicant_id, hashed=hashed, ip=ip,
                            minutes=settings.signin_link_minutes)
    append_event(conn, actor=f"applicant:{applicant_id}", kind="signin.requested",
                 payload={"applicant_id": applicant_id})
    return {"status": "sent"}


@router.post("/api/auth/verify")
def verify(body: VerifyRequest, request: Request, response: Response,
           conn: Connection = Depends(get_conn)):
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
def me(applicant: auth.Applicant = Depends(auth.require_applicant)):
    return {"email": applicant.email, "role": applicant.role}


@router.post("/api/auth/sign-out", status_code=204)
def sign_out(request: Request, conn: Connection = Depends(get_conn)):
    token = request.cookies.get(auth.SESSION_COOKIE)
    applicant_id = auth.revoke_session(conn, token) if token else None
    if applicant_id:
        append_event(conn, actor=f"applicant:{applicant_id}", kind="signin.signed_out",
                     payload={"applicant_id": applicant_id})
    response = Response(status_code=204)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return response
