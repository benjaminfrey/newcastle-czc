# Applicant Portal

The public web app where applicants find out which permit they need and apply for it.
Design: `specs/2026-10-14-applicant-portal-design.md`. Plans: `plans/2026-10-14-applicant-portal-*.md`.

## Development

Development runs on a VM, not the Mac. The Mac holds the git checkout and the editor;
`portal/vm.sh` copies `portal/` to the VM (`~/newcastle-czc/portal/`) and runs commands there.
The VM is `ben@192.168.1.6` unless `PORTAL_DEV_VM` says otherwise. Everything on the VM listens
on 127.0.0.1 only; `portal/vm.sh tunnel` forwards the dev ports to the Mac.

Start the database and the mail catcher (Mailpit, web view at http://127.0.0.1:8025 through the tunnel):

    portal/vm.sh run 'sudo docker compose -f portal/deploy/compose.dev.yml up -d --wait'

API, first time:

    portal/vm.sh run 'cd portal/api && python3.14 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt'

API, every time:

    portal/vm.sh run 'cd portal/api && .venv/bin/pytest'
    portal/vm.sh run 'cd portal/api && .venv/bin/python -m alembic upgrade head'
    portal/vm.sh run 'cd portal/api && PORTAL_COOKIE_SECURE=false .venv/bin/uvicorn portal_api.main:create_app --factory --port 8000'

Web app:

    portal/vm.sh run 'cd portal/web && npm ci && npm test'
    portal/vm.sh run 'cd portal/web && npm run dev'      # then http://localhost:5173 through the tunnel

In another terminal on the Mac, while working in a browser:

    portal/vm.sh tunnel
