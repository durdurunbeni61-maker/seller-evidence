# Security

Release 0.1.x is an early-stage, locally tested release candidate. There is no
commercial support, response-time guarantee, remote service or credential store.

## Report a vulnerability

After public release, use GitHub's private vulnerability reporting under Security
if the maintainer has enabled it. If unavailable, open a minimal issue requesting
a private reporting channel **without including exploit details, personal data,
secrets or real exports**. Until a public repository exists, report privately to
the maintainer through the existing communication channel.

## Boundaries

- Local CSV and SQLite only; no network imports in runtime or scripts.
- Exact allowlisted columns; no customer/order/contact input schema.
- Unknown numeric input remains unknown, never a fabricated zero.
- Input file/row limits, duplicate and overlap checks, bound SQL values.
- No marketplace scraping, API writes or automatic publishing.
- No user-data fixtures or databases in distributed files.

These checks are not anonymization or a complete security audit. Free text can
contain PII; inspect it manually. Local databases/output need your OS protections.
Do not process untrusted files without normal OS precautions. Export results only
to authorized recipients. Avoid uploading reports in public issues.

The release guard checks filenames, common secret/PII patterns, local paths and
network-related imports. Its pattern checks can miss secrets. The maintainer also
ran Gitleaks on the release candidate; see local review evidence. Build tooling and
GitHub Actions may contact package registries; runtime never contacts a marketplace.
