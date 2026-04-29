# Hetzner Recovery TODO

## Status Snapshot (April 2026)

- **Railway** hosts the consumer app (frontend + backend).
- **Hetzner** (`116.203.202.190`) is scraper infrastructure only — no app serving.
- Server is healthy: 8GB RAM, 150GB disk (15% used), up 21+ days.
- Cron runs `run_scrapers.sh` daily at 6 AM UTC (as root).
- **Phase 1 works** — collects ~39k URLs across all 3 pharmacies (Punto Farma, Farma Center, Farmacia Catedral).
- **Phase 2 was broken** — two issues found and partially fixed:
  1. ~~Chromium refused to launch as root without `--no-sandbox`~~ — fixed via `git pull` (commit `14ec1a4`).
  2. **RLS on `price_history` blocks writes** — `log_price_change()` trigger runs as anon role, which can't INSERT into `price_history`. Fix: run `sql/fix_log_price_change_security_definer.sql` in Supabase SQL editor.
- Farma Oliva is **not in the cron** — `run_scrapers.sh` only runs Punto Farma, Farma Center, Farmacia Catedral.
- Scrapers already expanded to **all categories** (commit `cb070d0`), not just medicamentos.
- Server `.env` uses anon key only — no `SUPABASE_SERVICE_ROLE_KEY`.

## Immediate Action Required

- [ ] **Run the RLS fix SQL in Supabase SQL editor** — `sql/fix_log_price_change_security_definer.sql`
  - Adds `SECURITY DEFINER` to `log_price_change()` so the trigger bypasses RLS.
  - Without this, every Phase 2 upsert fails with "violates row-level security policy for table price_history".
- [ ] After applying the SQL fix, test Phase 2 manually on the server:
  ```bash
  cd /opt/pharma-intelligence && source venv/bin/activate
  PHASE2_LIMIT=5 python -m scrapers.punto_farma phase2
  ```
- [ ] Verify products are saved to Supabase after the test.

## Decisions (Resolved)

- [x] **Railway** is the public app host; **Hetzner** is scraper infrastructure only.
- [x] Deployment model: **cron + Python venv** (already running on server).
- [x] Canonical pharmacy id for Farma Center: `farma_center` (matches DB).

## P0: Recover The Current Hetzner Server

- [x] SSH into the Hetzner box and confirm the machine is healthy.
  - 8GB RAM, 150GB disk (15% used), Ubuntu, up 21+ days, load ~0.01.
- [x] Inventory what is actually running.
  - Cron: `0 6 * * * /opt/pharma-intelligence/run_scrapers.sh`
  - No systemd timers. No Docker. No pm2.
  - Python 3.12 venv at `/opt/pharma-intelligence/venv/`.
  - Crawlee 1.6.0 installed.
- [x] Confirm the failure mode:
  - **Root cause 1**: Chromium sandbox fails when running as root without `--no-sandbox`. Fixed by pulling commit `14ec1a4`.
  - **Root cause 2**: `price_history` RLS blocks anon-key writes from the trigger. Fix: apply `SECURITY DEFINER` migration.
- [x] Preserve current logs — logs exist in `/opt/pharma-intelligence/logs/` going back to March 28.

## P0: Fix Repo-Level Deployment Blockers

- [x] Clean up stale deployment references in docs (CLAUDE.md, README.md).
- [x] Create `scripts/run_full_scrape.sh` — production entrypoint for all 4 pharmacies.
- [x] Normalize Farma Center naming to `farma_center` everywhere.
- [x] Fix `.env.example` — removed real keys, fixed `hhttps://` typo, added service role key.
- [x] Audit localhost defaults — fine for dev, Railway sets env vars in production.
- [x] Deploy artifacts created in `deploy/` directory:
  - `bootstrap.sh`, `update.sh`, `healthcheck.sh`
  - `systemd/` units and timers
  - `logrotate.d/pharma-scrapers`
  - `.env.example` for scraper runtime
- [ ] Create a daily tracker production entrypoint.

## P1: Server Hardening

- [ ] Set timezone to `America/Asuncion` — currently UTC.
- [ ] Add Farma Oliva to `run_scrapers.sh` (currently missing from cron).
- [ ] Consider switching from cron to systemd timers (deploy/systemd/ already created).
- [ ] Add `SUPABASE_SERVICE_ROLE_KEY` to server `.env` (currently anon-only).
- [ ] Lock down `.env` file permissions (`chmod 600`).
- [ ] Rotate Supabase anon key (it was committed to `.env.example` in the past).
- [ ] Add `logrotate` — logs are accumulating (~700KB/day, no rotation).
- [ ] Add `healthcheck.sh` to cron for daily validation.

## P1: Secrets, Data, And DB Safety

- [x] Confirmed scrapers need service role key for writes through RLS triggers.
- [ ] Add `SUPABASE_SERVICE_ROLE_KEY` to server `.env`.
- [ ] Verify required tables exist in Supabase:
  - `products`, `product_urls`, `scraping_runs`, `scraping_checkpoints`
  - `barcode_tracking_urls`, `barcode_tracking_snapshots`, `price_history`
- [ ] Verify `sql/fix_log_price_change_security_definer.sql` has been applied.

## P2: Data And Scraper Correctness

- [ ] Farma Oliva: finish the documented 2-phase rewrite for all categories.
- [x] Punto Farma: expanded to all 8 categories (commit `cb070d0`).
- [x] Farmacia Center: expanded to all 8 categories + image fix (commit `cb070d0`).
- [x] Farmacia Center: normalized to `farma_center` everywhere.
- [x] Farmacia Catedral: expanded to 11 categories (commit `cb070d0`).
- [ ] Validate category counts against current database counts after first successful Phase 2 run.
- [ ] Add a post-run validation script.

## Detailed Scraper Expansion Reference

### Farma Oliva

- Current state: single-phase Playwright, medicamentos + suplementos only.
- Target: move to a 2-phase flow and scrape the full catalog.
- Observed site changes:
  - migrated from WooCommerce to Dattamax
  - catalog supports `?ajax=true`
  - detail selectors still appear usable
- Recommended Phase 1:
  - collect URLs from `https://www.farmaoliva.com.py/catalogo.{page}?ajax=true`
- Recommended Phase 2:
  - scrape product detail pages with Playwright
- Best shortcut:
  - use `/catalogo.{page}?ajax=true` without a category filter to get the full catalog
- Reference counts:
  - medicamentos: 3,947
  - belleza: 1,887
  - cuidado personal: 1,652
  - dermocosmetica: 1,052
  - infantiles: 1,041
  - suplementos: 591
  - fragancias: 487
  - perfumes: 376
  - juguetes y peluches: 194
  - panales: 97
  - bienestar sexual: 68
  - total: 11,403

### Punto Farma

- Current state: **all 8 categories** configured in `collect_urls_from_api()` (lines 367-376).
- Categories: medicamentos, perfumes-y-fragancias, bebe-y-mama, cosmeticos, higiene, salud, nutricion-y-deporte, mundo-dermocosmetica.
- Important risk: the `next-action` header hash may change when Punto Farma deploys a new site version.

### Farmacia Center

- Current state: **all 8 categories** configured in `collect_urls_from_pages()` (lines 316-325).
- Categories: medicamentos, belleza, higiene, cuidado-de-la-salud, bebes, bazar-y-hogar, alimentos, infantiles.

### Farmacia Catedral

- Current state: **11 categories** configured in `collect_urls_from_api()` (lines 300-312).
- Categories: medicamentos, cuidado-corporal, cuidado-de-la-piel, maquillajes, cuidado-personal, cuidado-capilar, suplemento-vitaminico-y-mineral, cremas-faciales-y-corporales, bebes-y-maternidad, dermocosmetica, perfumes-y-fragancias.

## Estimated Product Counts After Expansion

| Pharmacy | Current | After expansion |
|----------|---------|-----------------|
| Farma Oliva | ~4,471 | ~11,403 |
| Punto Farma | ~5,360 | ~21,120 (actual from Phase 1) |
| Farmacia Center | ~4,232 | ~9,817 (actual from Phase 1) |
| Farmacia Catedral | ~4,857 | ~11,018 (actual from Phase 1) |
| Total | ~17,953 | ~53,000+ |

## Future / Nice To Have

- [ ] BigQuery sync from Supabase.
- [ ] dbt transformations.
- [ ] Looker Studio dashboards.
- [ ] AI product matching for products without barcodes.
- [ ] Client catalog matching.
- [ ] Custom domain for PrecioFarma.

## Definition Of Done

- [x] Hetzner server is running and healthy.
- [x] Code is up to date on server (`git pull` done).
- [x] Daily cron fires Phase 1 + Phase 2 for 3 pharmacies.
- [ ] Phase 2 actually saves products (blocked on RLS fix).
- [ ] Farma Oliva added to daily cron.
- [ ] Logs rotate and failures alert somewhere.
- [ ] Railway app continues to use the correct production URLs.
- [ ] Supabase shows fresh data after an automated run.
