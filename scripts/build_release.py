"""Build only from tracked files; never package runtime data or secrets."""

import hashlib
import subprocess
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = (
    subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
)
if not any(files):
    raise SystemExit("Stage the release source before packaging.")
out = root / "dist"
out.mkdir(exist_ok=True)
release_name = "Cafe-LUX-Version-1.3-Explore"
archive = out / (release_name + ".zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for name in files:
        if not name:
            continue
        path = Path(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.parts[0] in (".git", ".venv", "data", "dist")
            or path.suffix in (".sqlite3", ".db", ".log", ".key")
            or path.name in (".env", "cafe-lux.local.json", "cafe-lux.local.json.tmp")
        ):
            raise SystemExit("Unsafe tracked release file: " + name)
        if path.suffix.lower() == ".bat":
            content = (
                (root / path)
                .read_bytes()
                .replace(b"\r\n", b"\n")
                .replace(b"\n", b"\r\n")
            )
            z.writestr(release_name + "/" + name, content)
        else:
            z.write(root / path, arcname=release_name + "/" + name)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / (archive.name + ".sha256")).write_text(checksum + "  " + archive.name + "\n")
print(archive)
print(checksum)
