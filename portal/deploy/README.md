# Deploying the Applicant Portal

The host needs Docker Engine with the Compose plugin and ports 80 and 443 open.

1. Copy the repository's `portal/` folder to the host (`portal/vm.sh sync` does this for the dev VM).
2. `cp portal/deploy/env.example portal/deploy/.env` and fill it in. Never commit `.env`.
3. `docker compose -f portal/deploy/compose.yml --env-file portal/deploy/.env up -d --build --wait`
4. Check: `curl -s https://$PORTAL_HOST/api/health` prints `{"status":"ok","db":"ok"}`.

Updating: sync the new code, then repeat step 3. Migrations run when the API container starts.

## Trial run on the dev VM

To try the production stack without putting it on the network, set in `.env`:
`PORTAL_HOST=localhost`, `PORTAL_TLS=tls internal`, `PORTAL_BIND=127.0.0.1`,
`SMTP_HOST=mail`, `SMTP_PORT=1025`, and add the trial overlay, which brings its own mail catcher:

    sudo docker compose -f compose.yml -f compose.trial.yml --env-file .env up -d --build --wait

Sign-in emails land in that Mailpit, at 127.0.0.1:8026 on the VM. Stop it with the same files and `down`.

## Moving to a managed platform later

Point `PORTAL_DATABASE_URL` at managed Postgres with PostGIS, run the `api` and `web` images on any
container host, and set the SMTP variables for the relay. Nothing in the code is tied to this VM.

The relay must accept plain SMTP without login for now; `SmtpMailer` does not yet do STARTTLS or
AUTH. Backups are set up in Milestone 7. Until then the database lives only in the `db` volume.
