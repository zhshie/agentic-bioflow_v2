# Cloud-burn reports, 2026-11

- AR08 - Adversarial review of cloud_cost.py, su.py, web_cost.py: the SU card and cloud cap miscount (default_site pricing, partial sums, in-flight runs at $0, unpriceable tasks dropping a run), 13 surviving findings.
- AR09 - Adversarial review of web.py and web_board.py: exponent-form numbers sent as text, lost-run Resume offers the action layer refuses, SVG served without a sandbox CSP, shared login bucket behind a proxy, 15 surviving findings.
- AR10 - Adversarial review of web_settings.py, web_launch.py, web_upload.py, uploads_web.py, actions/uploads.py: same-name uploads overwrite registered dataset objects, resume-edit refuses its own untouched box, unregistered batches after job prune, 15 surviving findings.
