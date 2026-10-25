---
version: 1
slug: "portal-web-src-app-tsx"
primary_target: "portal/web/src/App.tsx"
related_targets: []
---

Scope: every applicant page of the Applicant Portal web app. Mode: Operate.
Audience and job: residents on phones and builders at desks, applying for a Town permit in about ten steps.
Spec: specs/2026-10-23-applicant-portal-redesign.md, revised by specs/2026-10-24-applicant-portal-wizard.md (one question at a time; the chair's choice after the prototype).

## Direction contract

Seed: canon (chair's explicit choice, 2026-10-23)

THESIS: One question at a time, moving sideways: the answers so far stack as chips above, plain dots below say where you are, and a single choice answers at a tap. The sections stay in the sidebar, so the application still reads as a document.

OWN-WORLD: Apple System Settings and iOS Settings grammar: grouped inset lists, a source-list sidebar, sheets, large titles; system UI type; the seal's teal #1098A8 for identity and selection, a deeper teal for actions; light and dark from the device.

STORY: Find out what you need, confirm your lot on the Town's map, answer one question at a time (values from the map just confirmed), review your answers in plain words.

FIRST VIEWPORT: Desktop, the step sidebar under the Town seal beside one centred question with its tiles, the trail above and the dots below; phone, the same question full width with ‹ Back above and the dots and Continue in the bottom bar.

SIGNATURE: Your lot's map, carried from "Your property" into "Is this right?", the setbacks around the lot drawing, and "Where it joins the road".

RISK: A web app imitating native chrome can feel uncanny: use native grammar, never fake window controls.
