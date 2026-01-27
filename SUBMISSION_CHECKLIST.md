# Submission Checklist

## Packaging checks
- 🔴 Verify `THESIS_SUBMISSION/` contains only the allowed directories and files.
- 🔴 Confirm no forbidden folders or artifacts are present (node_modules, .venv, .git, dist/build, __pycache__, *.pyc, *.db, *.log, .env, caches).
- 🟠 Sanity-check the archive size to ensure it matches a source-only submission.

## Writing checks
- 🔴 Ensure all claims in `README.md` are traceable to code or citations.
- 🟠 Add citations for any algorithms or concepts not authored here.
- 🟡 Confirm limitations and scope are stated clearly and consistently.

## Final sanity checks
- 🔴 Search for secrets or tokens and replace with placeholders; keep only `.env.example`.
- 🟠 Rebuild the submission zip and re-verify contents from a clean workspace.
- 🟡 Run a quick smoke test if required by the thesis guidelines.
