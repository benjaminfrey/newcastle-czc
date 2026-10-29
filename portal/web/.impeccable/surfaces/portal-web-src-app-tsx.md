---
version: 1
slug: "portal-web-src-app-tsx"
primary_target: "portal/web/src/App.tsx"
related_targets: []
---

Scope: every applicant page of the Applicant Portal web app. Mode: Operate.
Audience and job: residents on phones and builders at desks, applying for a Town permit as a short list of tasks.
Spec: specs/2026-10-25-applicant-portal-task-list.md (tasks and cards, approved 2026-10-25), revising specs/2026-10-24-applicant-portal-wizard.md and specs/2026-10-23-applicant-portal-redesign.md. Comp (binding): specs/assets/2026-10-25-task-list-comp.html.

## Direction contract

Seed: canon (chair's explicit choice, 2026-10-23)

THESIS: A short list of tasks, each a run of contained cards: one decision, or one set of values read off the same thing, to a card; a bar in the card's header counts the task's cards; a single choice answers at a tap; each task ends on its check page, and buildings are a list you add to, copy and check.

OWN-WORLD: Apple System Settings and iOS Settings grammar: grouped inset lists, a source-list sidebar, sheets, large titles; system UI type; the seal's teal #1098A8 for identity and selection, a deeper teal for actions; light and dark from the device.

STORY: Find out what you need, confirm your lot on the Town's map, answer one question at a time (values from the map just confirmed), review your answers in plain words.

FIRST VIEWPORT: Desktop, the task list (pills: Done, "2 of 4", Not started) in the sidebar under the Town seal beside one centred 640 px card — header with the bar, the question at 20 px, icon tiles, footer with Back and a near-black Continue; phone, ‹ Tasks above the same card filling the screen in 12 px gutters.

SIGNATURE: Your lot's map, carried from "Your property" into "Is this right?", the setbacks around the lot drawing, and "Where it joins the road".

RISK: A web app imitating native chrome can feel uncanny: use native grammar, never fake window controls.
