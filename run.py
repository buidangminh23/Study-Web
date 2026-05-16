import os
import threading

import uvicorn


def _start_auto_deploy():
    try:
        from auto_deploy import run
        t = threading.Thread(target=run, daemon=True, name="auto-deploy")
        t.start()
    except Exception as e:
        print(f"[auto-deploy] Could not start: {e}")


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8036"))
    _start_auto_deploy()
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()

