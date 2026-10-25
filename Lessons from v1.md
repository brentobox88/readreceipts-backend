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
  FF D8 FF â†’ JPEG
  89 50 4E â†’ PNG
  00 00 00 xx 66 74 79 70 â†’ HEIC
Telling you what the format actually is.
## PowerShell 5.1 writes UTF-8 BOM by default

`Set-Content -Encoding UTF8` and `Export-Csv -Encoding UTF8` write a UTF-8 BOM
(EF BB BF). Python's `csv.DictReader(f.open(encoding='utf-8'))` does NOT strip
the BOM, so the first column name becomes `'\ufeffimage_file'` and any
`row['image_file']` lookup raises KeyError.

Additionally, `Export-Csv` may re-quote headers when it detects the BOM,
producing headers like `'\ufeff\"image_file\"'` — doubly broken.

**Always** write files Python reads with:

    [System.IO.File]::WriteAllText(
        \,
        \,
        (New-Object System.Text.UTF8Encoding \False)  # <- no BOM
    )

This bit us 4 times in one session. Don't let it bit you again.

## Ghost errors = wrong file

The tell: **an error message stays byte-identical after every fix you make.**
That's not "the fix is wrong" — it's "the tool is reading a different file."

Fifth occurrence in one session:
1. `.env.backup` committed to git instead of excluded
2. `handler.py` v7 edits not in the Docker build (cache)
3. `tasks.py` confidence fix never made it into a commit
4. `test_set.csv` BOM added by PowerShell's Export-Csv
5. `ConfirmationScreen.tsx` — tsc reading a stale root-level copy while
   edits went into `src/screens/ConfirmationScreen.tsx`

When tsc / pytest / docker / git show errors that don't match the source:
- Run the tool with a "list what I'm actually reading" flag
  (`tsc --listFiles`, `git show HEAD:file`, `docker inspect --format '{{.Config.Image}}'`)
- Search for duplicate files with `Get-ChildItem -Filter "filename" -Recurse`
- Verify the tool's working directory / config matches the file you edited

## Session 2026-10-25: line items, worker v7, mobile edit flow

What shipped:
- Qwen worker v7 prompt (line items + date year accuracy)
- 15 recoverable receipts reprocessed with real itemized breakdown
- Mobile ReceiptDetailScreen renders line-item objects
- Mobile ConfirmationScreen modal dismiss (no more nav error)
- Deleted stale root-level ConfirmationScreen.tsx (tsc was reading it)
- Eval baseline: merchant 88.9% / total 100% / date 88.9% / tax 100%
- Baseline committed: evaluation/baseline_2026-10-25.json

What broke (and got fixed):
- CSV BOM from PowerShell Export-Csv
- Qwen v7 Docker image didn't deploy for hours (build cache)
- Phantom TypeScript errors from stale duplicate file

What's still on the backlog:
- EAS build + TestFlight
- Worker cron pattern (Render free-tier reliability)
- qwen-v8 prompt (26->23 year misread)
- Merchant fuzzy matching
