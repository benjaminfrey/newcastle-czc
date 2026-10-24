# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Residents** of Newcastle, Maine, applying once or rarely, usually with no zoning background,
  often older, often on a phone. They want to know whether they need a permit and to get the
  application done without calling the Town Office.
- **Repeat applicants**: builders, surveyors and architects who apply often, usually at a desk.
- The chair's ruling (2026-10-23): serve both equally — phone-first for residents, with desktop
  accelerators (keyboard, wider panes) for repeat applicants.
- Later (Milestone 6): Town staff (Code Enforcement Officer, Town Office) in a staff inbox.

## Product Purpose

The Town's public permit portal: "Do I need a permit?" (a screener answered from the adopted Code),
then a short wizard that builds the Town's official application form, which the applicant reviews,
edits and (from Milestone 6) signs and submits. Success: a resident with no zoning background
completes a complete application without calling the Town Office, and reviewers stop receiving
forms with blank districts and sticky-note questions.

## Positioning

The answers come from the Town's own adopted Code (Core Zoning Code v1.0, adopted September 14,
2026), pinned and cited section by section, and from the Town's own maps (parcels, districts, the
Street Type inventory). Every question can show the Code text it rests on ("Why we ask").

## Operating Context

- Applications: Use Permit (Art. 8 §15), Small Project Plan (Art. 8 §10), Entrance / Driveway
  Permit (Art. 3 §13.c.1). Other application types are explained and sent to the Town Office.
- Sign-in is by emailed link; drafts save as the applicant goes; uploads (PDF, JPEG, PNG, HEIC,
  25 MB) are virus-scanned.
- The printed official form uses the Code's exact terms; questions use plain words.
- Reviewing authorities: the Code Enforcement Officer, the Planning Board.

## Capabilities and Constraints

- Stack: React 19, HeroUI 3 (React Aria), Tailwind 4, Vite; FastAPI + Postgres/PostGIS API.
- **The software never decides**: no "approved", "denied", "compliant", "meets", "fails",
  "violates" outside a recorded staff decision (a test enforces this).
- Every question and form field is approved by the Planning Board chair before production serves
  it; wording changes go back to draft.
- An application keeps the form version it started on.
- Development runs on a VM; the portal is never on the public internet during development.

## Brand Commitments

- The Town of Newcastle's seal may be used in the portal (chair, 2026-10-23); it appears on the
  paper application forms. A clean digital copy is still to be supplied (none is in the repo).
- The chair's binding direction for the interface (2026-10-23): it should look and feel as close
  to a macOS / iOS app as possible, including how navigation (back / forward / continue) works.
- Voice: plain, calm, about an 8th-grade reading level; the Code's terms only on the official form.

## Evidence on Hand

- The adopted Code and its ruleset (`build/permit-review/rulesets/adopted-v1.0/`), the parcel,
  district and street data, and the Town's scanned paper forms (`docs/Findings of Fact and
  Conclusions of Law/`). No testimonials, usage numbers or endorsements exist; do not invent any.

## Product Principles

1. Fewer, better steps: an application should take about ten steps, not dozens.
2. Always show where the applicant is and what is left.
3. Never a verdict; always the Code's own words one tap away.
4. Nothing is lost: answers save as given, and a second tab never silently overwrites.
5. One portal for a resident on a phone and a builder at a desk.

## Accessibility & Inclusion

WCAG 2.1 AA (spec §4), usable one-handed on a phone; checked by axe in the Playwright journeys.
Older residents are a core audience: legible type, large targets, no time limits on screens.
