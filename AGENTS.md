# Repository Workflow

- Communicate with the project owner in Vietnamese.
- Keep generated source code in English.
- Do not add code comments unless explicitly requested.
- After any code change, documentation change, configuration change, or repo maintenance task, run the relevant checks before finishing.
- After checks pass, commit the completed work and push it to `origin/main`.
- Do not push broken work unless the project owner explicitly asks to save a failing state.
- Do not commit local runtime artifacts such as `.venv`, `.env`, `study_web.db`, caches, or generated temporary files.
- Keep each subject under its own folder in `app/content/subjects/`.
- The shared local run command is `python run.py`, with default port `8036`.
