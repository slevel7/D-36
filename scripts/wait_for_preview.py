"""Bounded readiness check for local development and CI."""

import time
import urllib.error
import urllib.request

for _attempt in range(60):
    try:
        with urllib.request.urlopen("http://127.0.0.1:3000", timeout=2) as response:
            if response.status == 200:
                print("Preview ready at http://127.0.0.1:3000")
                break
    except (urllib.error.URLError, TimeoutError):
        time.sleep(1)
else:
    raise SystemExit("Preview did not become ready; inspect the web/API logs")
