# v2 startup — known issues & lessons learned

Notes from the first real local run of `customer-compass-v2`, right after the
infra migration PR (Qdrant + Ollama cache reuse). Keep this updated as new
startup quirks are found — especially while v1 (`customer-compass`) and v2
coexist on the same machine.

## 1. `db` container name clash with v1 (fixed)

**Symptom:** UI shows *"Could not reach the API. Start PostgreSQL and the
API, then refresh."* even though the API process is running.

**Cause:** v2's `docker-compose.yml` initially reused v1's exact container
name (`customer-compass-db`). If a stopped v1 `customer-compass-db` container
already exists on the machine, `docker-compose up` fails to (re)create v2's
`db` with the same name — and depending on compose version, this can abort
the whole `up` command partway (see #2 below).

**Fix applied:** v2's `db` container is now named `customer-compass-v2-db`,
matching the naming already used for `ollama`/`qdrant`. No action needed
going forward — just make sure you're on a version of this repo that
includes that fix.

## 2. A failed service can silently abort the whole `docker-compose up`

**Symptom:** You ran `docker-compose up -d db qdrant ollama`, but afterwards
`ollama` (or another service) wasn't actually running — `docker ps` shows
nothing, or `docker ps -a` shows it stuck in `Created` state (never
`Started`).

**Cause:** If one service in the same `up` command fails to create (e.g. the
container-name clash in #1), some Docker Compose versions skip starting the
remaining services in that invocation entirely, even though they report
"Created" successfully.

**Lesson:** After *any* `docker-compose up`, don't just trust the command's
output — verify all expected containers are actually in the `Up` state:
```bash
docker ps --format "{{.Names}}\t{{.Status}}"
```
If something is missing or stuck at `Created`, re-run `docker-compose up -d
<missing-service>` explicitly for just that service.

## 3. Full startup needs three containers, not just `db`

The API depends on **all three** infra containers — Postgres, Qdrant, and
Ollama. Starting only `db` will let the API process boot, but any chat
request will fail (500/503) because Ollama (generation) isn't reachable.

Always start all three together:
```bash
docker-compose up -d db qdrant ollama
```

## 4. v1 and v2 can't run `db`/`ollama` at the same time

Both repos' Postgres and Ollama services bind the **same host ports** (5432,
11435) regardless of container name. Only one stack (v1 or v2) can have
these services running at once — stop one (`docker-compose down`) before
starting the other.

## 5. `apps/api/.env` is per-repo, not shared

v1 and v2 are separate clones with separate `apps/api/.env` files (gitignored
in both). Setting `OPENROUTER_API_KEY` in v1's `.env` does **not**
automatically apply to v2 — copy it over manually if reusing the same key:
```bash
cp ../customer-compass/apps/api/.env apps/api/.env
```
Then restart `npm run dev` (env vars are loaded once at process start, not
hot-reloaded on `.env` changes).

## 6. Free-tier OpenRouter cloud models are inconsistent — not a bug

Occasionally picking a free OpenRouter model returns *"The cloud model
returned an empty response. Try again or pick a different model."* This is
expected: free-tier models route through shared, rate-limited community
infrastructure and can return a `200 OK` with no actual content. The app
already distinguishes this case from a hard error (see
`apps/api/src/llm/cloud.ts`). If it happens, just retry or pick a different
model from the dropdown — it isn't specific to v2.

## 7. Dropdown "selected value" can look wrong due to shared browser storage

v1 and v2 both run on `localhost:5173` (same origin). Chat mode / provider /
cloud-model selections are persisted to `localStorage`, which is shared by
origin, not by repo — so a selection made while testing v1 can appear as the
"default" when you later open v2 in the same browser. Clear it if needed:
```js
localStorage.clear()
```
(Removing this persistence entirely, or namespacing the storage keys per
repo, is a possible follow-up — not yet done as of this PR.)
