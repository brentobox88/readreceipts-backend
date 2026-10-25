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
## PowerShell 5.1 writes UTF-8 BOM by default

`Set-Content -Encoding UTF8` and `Export-Csv -Encoding UTF8` write a UTF-8 BOM
(EF BB BF). Python's `csv.DictReader(f.open(encoding='utf-8'))` does NOT strip
the BOM, so the first column name becomes `'\ufeffimage_file'` and any
`row['image_file']` lookup raises KeyError.

Additionally, `Export-Csv` may re-quote headers when it detects the BOM,
producing headers like `'\ufeff\"image_file\"'` � doubly broken.

**Always** write files Python reads with:

    [System.IO.File]::WriteAllText(
        \,
        \,
        (New-Object System.Text.UTF8Encoding \False)  # <- no BOM
    )

This bit us 4 times in one session. Don't let it bit you again.
