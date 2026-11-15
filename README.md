# EventSphere - agent-based venue booking and ticketing (IT4123 ICA 02)

FastAPI + SQLAlchemy + Jinja/Bootstrap. All booking, hire, ticketing and waitlist decisions are made by five
cooperating agents that talk only through JSON messages on a message bus (every message is logged).

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # then export the variables (or set them in your shell)
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 . SQLite is used by default; demo data is seeded on first start (`SEED_DEMO=1`).

## Environment variables
| Name | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite locally, PostgreSQL in production | `sqlite:///./eventsphere.db` |
| `SECRET_KEY` | signs session cookies (**set a long random value in production**) | dev value |
| `APP_TIMEZONE` | timezone for all event times | `Asia/Colombo` |
| `HTTPS_ONLY` | `1` makes the session cookie Secure (use on Render) | `0` |
| `SEED_DEMO` | create demo users, venues, events when DB is empty | `1` |
| `ENABLE_SCHEDULER` | run the WaitlistAgent expiry sweep every 30 s | `1` |
| `HOLD_MINUTES` | waitlist seat-hold length | `10` |
| `AGENT_API_KEY` | key for the HTTP agent inboxes (`X-Agent-Key`); blank disables them | blank |

Secrets are never committed (`.env` is git-ignored).

## Demo accounts
| Role | Email | Password |
|---|---|---|
| admin | admin@eventsphere.test | Admin#12345 |
| staff | staff@eventsphere.test | Staff#12345 |
| attendee | attendee@eventsphere.test | Attendee#12345 |

Change or remove these before a public demo if you prefer (edit `app/seed.py`).

## Tests
```bash
pytest -v
```
30 tests: security/CSRF/roles, every agent's rules, overbooking under 12 concurrent threads, double check-in,
hold expiry + re-offer, message traceability, HTTP inbox.

## Deploy on Render
1. Push to GitHub (add the lecturer as collaborator if private).
2. Render -> New -> Blueprint -> select the repo (`render.yaml` creates the web service and a PostgreSQL database
   and generates `SECRET_KEY` and `AGENT_API_KEY`). Or create them manually with the env vars above.
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Open the live URL before the viva (free tier sleeps). The waitlist scheduler runs inside the web process.

## Project layout
```
app/
  main.py            app factory, middleware, error handling, scheduler start
  config.py          settings and every business-rule constant
  database.py        engine/session (SQLite or PostgreSQL)
  models.py          tables (incl. agent_messages log and agent_state beliefs)
  schemas.py         Pydantic validation
  security.py        PBKDF2 hashing, sessions, role dependency, CSRF, flash
  policy.py          refund policy (shared display helper)
  agents/
    messages.py      JSON envelope + performatives
    bus.py           bus: logs every message, delivers, broadcasts
    base.py          Agent base class, persistent beliefs
    venue_agent.py booking_agent.py ticket_agent.py waitlist_agent.py notification_agent.py
    registry.py      builds the bus; helper for user -> agent requests
    scheduler.py     30 s proactive sweep
  routers/           auth, public (attendee), hire, staff, admin, api (HTTP agent inboxes)
  templates/ static/ Bootstrap pages, QR/scanner JS, countdown JS
tests/               pytest suite
```

## HTTP agent inboxes (advanced feature)
```bash
curl -X POST $URL/api/agents/TicketAgent/inbox -H "X-Agent-Key: $AGENT_API_KEY" -H "Content-Type: application/json" \
  -d '{"sender":"demo","performative":"REQUEST","content":{"action":"scan","code":"abc","event_id":1}}'
```
Interactive docs: `/docs`.

## Advanced features implemented
Waitlist with timed holds, visible countdown and automatic re-offer; weekend/peak hire pricing; suspicious repeated
scan detection; HTTP agent inboxes; dashboard chart; advanced search (venue, max price, date).
