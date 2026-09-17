# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Money-Pot is a Flask-based grocery budgeting web app (MVP/early development). Users create an
account and land in a personal "Money Pot" (a shared weekly budget); they can invite others into
that pot (or join someone else's via an invite link) to log grocery purchases collaboratively, and
can look up product info via the Open Food Facts API. See README.md for full product context and
roadmap, and `shared-money-pots-implementation-plan.txt` for the design rationale behind the
Pot/Membership model below.

## Running the app

```bash
source venv/bin/activate        # activate the existing virtualenv
pip install -r requirements.txt
flask db upgrade                # applies migrations/ to create/update instance/database.db
python app.py                   # runs Flask dev server on http://127.0.0.1:5000 with debug=True
```

Requires a `.env` file (gitignored) with:
- `SECRET_KEY` — Flask session secret
- `DATABASE_URL` — optional Postgres/Supabase URL; falls back to local `sqlite:///database.db` if unset

There is no build step or linter configured in this repo.

### Running tests

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

`tests/conftest.py` points `SQLALCHEMY_DATABASE_URI` at a fresh temp-file SQLite database (session
lifetime, reset via `drop_all`/`create_all` around every test) — it does not touch
`instance/database.db`.

## Architecture

Everything lives in a single `app.py` (Flask, no blueprints/app factory). Key things to know:

- **Models** (`app.py`): `User`, `Pot`, `Membership`, `GroceryItem`, all via Flask-SQLAlchemy.
  - Many-to-many `User` &harr; `Pot` via `Membership`, which also carries `role` (`'owner'` or
    `'member'`). A user always has at least one pot, but that's an *application-level*, not a
    database-level, guarantee — see `get_active_pot()` below.
  - Pot ownership is derived from `Membership.role == 'owner'`, not stored redundantly on `Pot`. A
    partial unique index (`uq_membership_one_owner_per_pot`) guarantees at most one owner row per
    pot; it cannot guarantee a pot always *has* one — that's enforced by keeping every
    ownership-transfer step (leave, remove-member) inside one transaction, plus a defensive
    `_assert_pot_has_owner()` check before commit.
  - `GroceryItem.pot_id` and `GroceryItem.added_by_user_id` replace the old `budget_id` +
    free-text `shopper` field — purchases are attributed to a real logged-in `User`.
  - Schema is managed by Flask-Migrate/Alembic (`migrations/`), not `db.create_all()`. Schema
    changes go through `flask db migrate -m "..."` + `flask db upgrade`, not manual DB deletion.
- **Auth**: still session-based (`session["username"]`), password hashes via `werkzeug.security`.
  `current_user()` and the `@login_required` decorator (`app.py`) replace the old copy-pasted
  `"username" not in session` checks in every route.
- **Active pot resolution**: `get_active_pot(user)` resolves `session["active_pot_id"]` to a real
  `Membership` on *every* call (not just at login), and self-heals by creating a fresh personal pot
  whenever a user has zero memberships — whether because they left their last pot, were removed by
  an owner, or their only pot was emptied out from under them. This is the single place that
  invariant is enforced; don't duplicate it in individual routes.
- **Authorization**: `/delete/<id>` and `/edit/<id>` check `Membership.query.filter_by(user_id=...,
  pot_id=item.pot_id)` before acting — keep this check intact on any route that touches a
  `GroceryItem` by ID. Owner-only actions (`/pots/<id>/invite/regenerate`,
  `/pots/<id>/members/<id>/remove`) check `role == "owner"` inline at the top of the route (no
  decorator — only a couple of routes need it).
- **Templates**: Jinja2 templates in `templates/`, extending `templates/base.html`; the pot
  switcher and "My Pots"/"Settings" nav links live in `templates/_sidebar.html`, included by every
  authenticated page. Routes and templates are paired 1:1 (e.g. `/lookup` &harr; `look_up.html`,
  `/pots` &harr; `pots_list.html`, `/pots/<id>/settings` &harr; `pot_settings.html`, `/join/<code>`
  &harr; `join_pot.html`).
- **External API**: `/lookup` and `/lookup/name` call `world.openfoodfacts.org` directly with
  `requests` (barcode lookup and name search respectively) and render results inline — no caching
  or API client abstraction.
- **Static assets**: plain CSS in `static/css/style.css` plus decorative SVG backgrounds; no
  frontend build tooling (no npm/bundler).

## Known gaps to be aware of

- No CSRF protection on forms.
- No rate limiting or account lockout on login/register.
- Rename-pot and delete-pot-as-an-owner-action are deferred (Phase 2, per the implementation plan)
  — an unwanted shared pot can still be fully removed by every member leaving it (last-member-leave
  auto-deletes the pot).
- `/edit/<id>` assigns `request.form['func']` to `GroceryItem.amount` without `int()`-converting it
  first — SQLite's column-affinity coercion happens to save it as an integer, but this is
  incidental, not validated input.
