import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from typing import Protocol


class MailError(Exception):
    """The message could not be handed to the relay."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class Mailer(Protocol):
    def send(self, email: Email) -> None: ...


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str):
        self.host, self.port, self.sender = host, port, sender

    def build(self, email: Email) -> EmailMessage:
        if any(c in email.to + email.subject for c in "\r\n"):
            raise MailError("line break in a header")
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = email.to
        msg["Subject"] = email.subject
        # A relay is not guaranteed to add these, and mailboxes refuse or junk mail without them.
        msg["Date"] = formatdate(localtime=False, usegmt=True)
        msg["Message-ID"] = make_msgid(domain=parseaddr(self.sender)[1].rpartition("@")[2] or None)
        msg.set_content(email.body)
        return msg

    def send(self, email: Email) -> None:
        msg = self.build(email)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.send_message(msg)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailError(str(exc)) from exc


@dataclass
class OutboxMailer:
    """For tests: keeps messages in memory; set fail=True to simulate a dead relay."""

    sent: list[Email] = field(default_factory=list)
    fail: bool = False

    def send(self, email: Email) -> None:
        if self.fail:
            raise MailError("simulated relay failure")
        self.sent.append(email)


def signin_email(to: str, link: str, minutes: int) -> Email:
    body = (
        "Hello,\n\n"
        "Here is your link to sign in to the Town of Newcastle permit applications site:\n\n"
        f"{link}\n\n"
        f"The link works once and stops working after {minutes} minutes.\n\n"
        "If you didn't ask for this, you can ignore this email. Nobody can sign in without the link.\n\n"
        "Town of Newcastle, Maine\n"
    )
    return Email(to=to, subject="Your sign-in link for Newcastle permits", body=body)
