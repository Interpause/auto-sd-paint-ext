import os
from pathlib import Path

from launch import commit_hash as get_commit_hash
from launch import git, run

REPO_LOCATION = Path(__file__).parent
LAST_BREAKING_COMMIT_TIME = 1674039585 # 26fd444811b6ce45845023a6d4a8bedcba53b60d
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
    cur_commit_time = run(f'{git} show -s --format=%ct {auto_commit_hash}')
    if int(cur_commit_time) < LAST_BREAKING_COMMIT_TIME:
        print(f"[auto-sd-paint-ext] Current A1111 commit is OLDER than the latest breaking changes! Extension might fail to function as expected!!!")
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
