import os
import subprocess
import threading

import uvicorn


def _start_auto_deploy():
    try:
        from auto_deploy import run
        t = threading.Thread(target=run, daemon=True, name="auto-deploy")
        t.start()
    except Exception as e:
        print(f"[auto-deploy] Could not start: {e}")


def _get_tailscale_host() -> str | None:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except Exception:
        return None
    host = result.stdout.strip().splitlines()
    return host[0].strip() if host and host[0].strip() else None


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8036"))
    tailscale_host = _get_tailscale_host()
    _start_auto_deploy()
    print(f"Study Web local: http://localhost:{port}")
    if tailscale_host:
        print(f"Study Web Tailscale: http://{tailscale_host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()

