# 🎟️ EventSphere — Multi-Agent Venue Booking & Ticketing Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![Bootstrap 5](https://img.shields.io/badge/Bootstrap-5.3-7952B3.svg?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest%20Passing-success.svg?logo=pytest&logoColor=white)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)

> **EventSphere** is an enterprise-grade venue booking, event management, and ticketing platform powered by a **decentralized Multi-Agent System (MAS)**. Built with FastAPI, SQLAlchemy, and Bootstrap 5, all business logic, booking approvals, venue hire negotiations, and waitlist allocations are handled by **5 autonomous agents** communicating through standard FIPA-ACL JSON messages over a persistent message bus.

---

## 🏛️ System Architecture & Autonomous Agents

EventSphere decouples core domain operations into five specialized, autonomous agents. Every decision, transition, and belief state update is logged for complete auditability.

```mermaid
flowchart TD
    Client(["🌐 Web Client / QR Scanner"]) <--> API["FastAPI Web Layer"]
    API <--> Bus[("🚌 Agent MessageBus (Logged)")]
    
    subgraph Agents ["🤖 Multi-Agent Ecosystem"]
        direction TB
        VA["🏛️ VenueAgent<br/><i>Venue hire, capacity & schedule</i>"]
        BA["🎫 BookingAgent<br/><i>Ticket reservations & inventory</i>"]
        TA["🔍 TicketAgent<br/><i>QR generation & gate check-in</i>"]
        WA["⏳ WaitlistAgent<br/><i>Timed holds & auto re-offering</i>"]
        NA["🔔 NotificationAgent<br/><i>In-app alerts & notifications</i>"]
    end
    
    Bus <--> VA
    Bus <--> BA
    Bus <--> TA
    Bus <--> WA
    Bus <--> NA
```

### The Agent Roster
* **🏛️ VenueAgent**: Evaluates venue hire requests, enforces buffer times, computes peak/weekend multipliers, and prevents schedule conflicts.
* **🎫 BookingAgent**: Governs ticket availability, atomic quantity deduction, basket hold validations, and purchase finalization.
* **🔍 TicketAgent**: Generates cryptographically secure ticket codes, renders QR codes, and detects duplicate or suspicious gate scans.
* **⏳ WaitlistAgent**: Manages queue allocations with a proactive 30-second scheduler sweep, releasing expired holds and notifying the next attendee in line.
* **🔔 NotificationAgent**: Listens to system-wide agent broadcasts and dispatches contextual user notifications.

---

## 🚀 How to Run Locally

### Prerequisites
* **Python 3.10+** (Python 3.11 or 3.12 recommended)
* **Git**

### Step-by-Step Setup

1. **Clone the repository and enter the project folder:**
   ```bash
   git clone https://github.com/your-username/EventSphere.git
   cd EventSphere
   ```

2. **Create and activate a virtual environment:**
   * **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   * **Windows (PowerShell / CMD):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Linux / macOS
   cp .env.example .env

   # Windows (PowerShell)
   Copy-Item .env.example .env
   ```

5. **Start the development server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

6. **Open in browser:**
   * **Web Application:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
   * **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   * **Alternative API Docs:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

> 💡 **Tip:** On initial launch with `SEED_DEMO=1`, the SQLite database (`eventsphere.db`) is automatically initialized and populated with sample venues, events, ticket categories, and demo user accounts.

---

## ⚙️ Environment Variables

Configure application settings by modifying `.env` or exporting system environment variables:

| Variable | Description | Default | Production Recommendation |
|:---|:---|:---:|:---|
| `DATABASE_URL` | SQLAlchemy connection string (SQLite or PostgreSQL) | `sqlite:///./eventsphere.db` | PostgreSQL connection string |
| `SECRET_KEY` | Cryptographic secret for signing session cookies | `dev-only-change-me` | 64+ char random hex string |
| `APP_TIMEZONE` | Timezone for event scheduling and display | `Asia/Colombo` | Local server / target timezone |
| `HTTPS_ONLY` | Enforces `Secure` flag on HTTP cookies (`1` to enable) | `0` | Set to `1` behind SSL/TLS |
| `SEED_DEMO` | Seeds sample events, venues, and users when DB is empty | `1` | Set to `0` in production |
| `ENABLE_SCHEDULER` | Runs the proactive 30s WaitlistAgent expiration sweep | `1` | `1` (leave enabled) |
| `HOLD_MINUTES` | Duration (in minutes) for waitlist seat-reservation holds | `10` | `5` – `15` depending on traffic |
| `AGENT_API_KEY` | Secret token required for external HTTP agent inboxes | `""` *(disabled)* | Strong API secret key |
