# Lessons from v1

## Verify file writes
After any PowerShell patch to a Python file, run:
  `git show HEAD:<file> | Select-String "<marker>"`
to confirm the change is in the commit, not just the working dir.

## Verify credential rotation everywhere
Rotating a DB password requires updating:
  - Local `.env`
  - Render API service env vars
  - Render worker service env vars
All three, every time.

## Check env vars across services
Each Render service (API, worker) has its own environment.
Rotating a secret means updating every service that uses it.

## Eval harness first
Without `evaluation/run_eval.py`, there's no way to know
if a change helped or hurt. Build the eval before
optimizing anything.

## HEIC is the enemy
iPhone photos are HEIC. Every image handler needs
`pillow_heif.register_heif_opener()` in the process
that decodes the image.

## Magic bytes don't lie
When an image fails to decode, check the first 3 bytes:
  FF D8 FF → JPEG
  89 50 4E → PNG
  00 00 00 xx 66 74 79 70 → HEIC
Telling you what the format actually is.