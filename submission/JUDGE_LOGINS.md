# Judge Logins

Login uses a role picker. **No password is checked** (`POST /api/auth/login` takes just a role). These are demo profiles with fictional names and addresses.

| Role | How to log in | What it unlocks |
|---|---|---|
| Analyst (recommended) | Choose "Crime Analyst" on the login page | All tabs: Investigation, Correlation Map, Incidents, Sources, Zetaris, Tip Triage |
| Admin | Choose "Police Chief / Admin" | All tabs, plus the executive overview |
| Officer | Choose "Station Officer" | Overview, Incidents, Tip Triage |
| Public | Choose "Public Citizen" | Overview, Tip Portal |

API equivalent:
```bash
curl -X POST localhost:8000/api/auth/login -H 'content-type: application/json' -d '{"role":"analyst"}'
```

Judge CLI, no login needed:
```bash
curl -X POST http://localhost:8000/run -H 'content-type: application/json' -d @input_examples/example_1.json
```

Offline, no credentials:
```bash
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true oah-submission
```
(Build the frontend first: `cd frontend && npm install && npm run build`; see `submission/README_NOTES.md`.)
