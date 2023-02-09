import os
from pathlib import Path

from launch import commit_hash as get_commit_hash
from launch import git, run

REPO_LOCATION = Path(__file__).parent
# git show -s --format=%ct <commit_hash>
LAST_BREAKING_COMMIT_TIME = 1675466396
LAST_BREAKING_COMMIT = "6c6c6636bb123d664999c888cda47a1f8bad635b"
auto_update = os.environ.get("AUTO_SD_PAINT_EXT_AUTO_UPDATE", "False").lower() in {
    "true",
    "yes",
}

try:
    commit_hash = run(f'{git} -C "{REPO_LOCATION}" rev-parse HEAD').strip()
except Exception:
    commit_hash = "<none>"

print(f"[auto-sd-paint-ext] Commit hash: {commit_hash}")

auto_commit_hash = get_commit_hash()
try:
    cur_commit_time = run(f"{git} show -s --format=%ct {auto_commit_hash}")
    if int(cur_commit_time) < LAST_BREAKING_COMMIT_TIME:
        print(
            f"[auto-sd-paint-ext] Current A1111 commit is OLDER than last breaking commit ({LAST_BREAKING_COMMIT})! Extension might fail to function as expected!!!"
        )
except Exception:
    pass

if auto_update:
    print("[auto-sd-paint-ext] Attempting auto-update...")

    try:
        run(f'"{git}" -C "{REPO_LOCATION}" pull', "[auto-sd-paint-ext] Pull upstream.")
    except Exception as e:
        print("[auto-sd-paint-ext] Auto-update failed:")
        print(e)
        print("[auto-sd-paint-ext] Ensure git was used to install extension.")
else:
    print("[auto-sd-paint-ext] Auto-update disabled.")

# NOTE: if we ever get dependencies, we can install them here.
