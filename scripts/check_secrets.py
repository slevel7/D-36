"""Lightweight pre-push pattern scan; not a substitute for full secret scanning."""

import re
import subprocess
from pathlib import Path

patterns = [
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"gh[pousr]_[A-Za-z0-9]{30,}",
    rb"AKIA[0-9A-Z]{16}",
]
files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
).split(b"\0")
findings = []
for raw in files:
    if not raw:
        continue
    path = Path(raw.decode("utf-8"))
    if not path.is_file():
        continue
    if any(re.search(pattern, path.read_bytes()) for pattern in patterns):
        findings.append(str(path))
if findings:
    raise SystemExit("Potential secrets in: " + ", ".join(findings))
print("PASS: no private key, GitHub token or AWS access-key patterns in tracked/unignored files")
