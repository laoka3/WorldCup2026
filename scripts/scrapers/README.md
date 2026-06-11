# Optional Scraper Adapters

Scrapers are a last-resort fallback and are disabled by default.

Run only when:

- `ENABLE_WEB_SCRAPING=true`
- the source allows access under its robots / terms
- the data is public and does not require login

Rules:

- Declare `source_name`, `source_url`, `allowed_by_robots_check`, `rate_limit_seconds`, and `fetched_at`.
- Do not bypass login, CAPTCHA, Cloudflare, paywalls, or other access controls.
- Do not use stealth browser techniques.
- Keep each domain rate limited, normally at least 10-30 seconds between requests.
- Write raw cache first, then transform into the standard cache format.
- If parsing fails, write a warning and do not fabricate data.

First stage status:

- Framework only.
- No concrete website scraper is enabled or implemented.
