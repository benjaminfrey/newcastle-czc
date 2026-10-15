# Deploying the Applicant Portal

The host needs Docker Engine with the Compose plugin and ports 80 and 443 open.

1. Copy the repository's `portal/` folder to the host (`portal/vm.sh sync` does this for the dev VM).
2. `cp portal/deploy/env.example portal/deploy/.env` and fill it in. Never commit `.env`.
3. `docker compose -f portal/deploy/compose.yml --env-file portal/deploy/.env up -d --build --wait`
4. Check: `curl -s https://$PORTAL_HOST/api/health` prints `{"status":"ok","db":"ok"}`.

Updating: sync the new code, then repeat step 3. Migrations run when the API container starts.

## The development stack on the LAN

During development the portal runs on the dev VM for the local network only: never port-forwarded,
never on the public internet. `.env` on the VM sets `PORTAL_HOST=<the VM's LAN address>`,
`PORTAL_TLS=tls internal`, `PORTAL_BIND=` (empty: every interface), `SMTP_HOST=mail`,
`SMTP_PORT=1025` and `MAILPIT_UI_AUTH=<user>:<password>`. The LAN overlay brings its own Mailpit;
sign-in emails appear at `http://<VM>:8026` behind that password.

    portal/vm.sh lan        # from the Mac: sync, rebuild, restart

Caddy signs the HTTPS certificate with its own local authority, so browsers warn once per device.
To stop the warning, trust Caddy's root certificate on that device; it is inside the `caddy-data`
volume at `/data/caddy/pki/authorities/local/root.crt`.

To keep a trial on the VM alone, set `PORTAL_BIND=127.0.0.1` instead.

### Property data on the LAN stack

The LAN stack sets `PORTAL_ALLOW_STALE_PARCELS=true` (development only). Load the GIS layers into
its database with the API image and the repo mounted read-only, e.g.

    sudo docker compose -f compose.yml -f compose.lan.yml --env-file .env run --rm -T \
      -v $HOME/newcastle-czc:/repo:ro api python -m portal_api.gis parcels --axisgis

(see `portal/README.md` for all four layers). Build the basemap (`portal/basemap/`) before
`vm.sh lan`, since the web image copies it in.

## Moving to a managed platform later

Point `PORTAL_DATABASE_URL` at managed Postgres with PostGIS, run the `api` and `web` images on any
container host, and set the SMTP variables for the relay. Nothing in the code is tied to this VM.

The relay must accept plain SMTP without login for now; `SmtpMailer` does not yet do STARTTLS or
AUTH. Backups are set up in Milestone 7. Until then the database lives only in the `db` volume.
