# Repository Workflow

- Communicate with the project owner in Vietnamese.
- Keep generated source code in English.
- Do not add code comments unless explicitly requested.
- Prefer GitHub-only edits for this repository: create, edit, delete, and commit files directly through GitHub APIs or GitHub CLI without modifying the local workspace.
- Do not create or edit files on the owner's PC/workspace unless the project owner explicitly asks for local work, local testing, or local app execution.
- If local verification is required, ask before touching local files or running commands that mutate the workspace.
- After any code change, documentation change, configuration change, or repo maintenance task, run the relevant checks when feasible before finishing.
- After checks pass, commit the completed work and push it to `origin/main`.
- Do not push broken work unless the project owner explicitly asks to save a failing state.
- Do not commit local runtime artifacts such as `.venv`, `.env`, `study_web.db`, caches, or generated temporary files.
- Keep each subject under its own folder in `app/content/subjects/`, and name that folder exactly after the subject title.
- The shared local run command is `python run.py`, with default port `8036`.