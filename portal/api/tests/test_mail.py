import httpx
import pytest

from portal_api.mail import Email, MailError, OutboxMailer, SmtpMailer, signin_email

MAILPIT = "http://127.0.0.1:8025/api/v1/messages"


def test_signin_email_is_plain_and_carries_the_link():
    e = signin_email("a@example.com", "https://x/signin/verify#token=abc", 15)
    assert e.to == "a@example.com"
    assert e.subject == "Your sign-in link for Newcastle permits"
    assert "https://x/signin/verify#token=abc" in e.body
    assert "15 minutes" in e.body
    assert "If you didn't ask for this" in e.body


def test_outbox_records_and_can_fail():
    box = OutboxMailer()
    box.send(Email("a@example.com", "s", "b"))
    assert box.sent == [Email("a@example.com", "s", "b")]
    box.fail = True
    with pytest.raises(MailError):
        box.send(Email("a@example.com", "s", "b"))


def test_header_injection_is_refused():
    with pytest.raises(MailError):
        SmtpMailer("127.0.0.1", 1025, "permits@localhost").send(
            Email("a@example.com\r\nBcc: x@evil.test", "s", "b")
        )


def test_smtp_mailer_delivers_to_mailpit():
    httpx.delete(MAILPIT)
    SmtpMailer("127.0.0.1", 1025, "Newcastle Permits <permits@localhost>").send(
        Email("dev@example.com", "Hello from the portal", "Body text")
    )
    msgs = httpx.get(MAILPIT).json()["messages"]
    assert [m["Subject"] for m in msgs] == ["Hello from the portal"]
    assert msgs[0]["To"][0]["Address"] == "dev@example.com"


def test_unreachable_relay_raises_mail_error():
    with pytest.raises(MailError):
        SmtpMailer("127.0.0.1", 1, "permits@localhost").send(Email("a@example.com", "s", "b"))


def test_messages_carry_date_and_message_id():
    # RFC 5322 requires Date; Gmail and others refuse or junk mail without a Message-ID,
    # and a relay is not guaranteed to add either. Sign-in depends on this mail arriving.
    msg = SmtpMailer("127.0.0.1", 1025, "Town of Newcastle Permits <permits@newcastle.example>").build(
        Email("a@example.com", "s", "b")
    )
    assert msg["Date"]
    assert msg["Message-ID"].startswith("<") and msg["Message-ID"].endswith("@newcastle.example>")
