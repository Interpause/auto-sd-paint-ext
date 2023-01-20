import os
from pathlib import Path

from launch import git, run

REPO_LOCATION = Path(__file__).parent
auto_update = os.environ.get("AUTO_SD_PAINT_EXT_AUTO_UPDATE", "False").lower() in {
    "true",
    "yes",
}

if auto_update:
    print("[auto-sd-paint-ext] Attempting auto-update...")

    try:
        # current_hash = run(
        #     f'"{git}" -C {REPO_LOCATION} rev-parse HEAD',
        #     "[auto-sd-paint-ext] Get commit hash.",
        # ).strip()

        run(
            f'"{git}" -C "{REPO_LOCATION}" fetch', "[auto-sd-paint-ext] Fetch upstream."
        )

        run(f'"{git}" -C "{REPO_LOCATION}" pull', "[auto-sd-paint-ext] Pull upstream.")
    except Exception as e:
        print("[auto-sd-paint-ext] Auto-update failed:")
        print(e)
        print("[auto-sd-paint-ext] Ensure git was used to install extension.")
else:
    print("[auto-sd-paint-ext] Auto-update disabled.")
    print(
        "[auto-sd-paint-ext] Enable auto-updates by setting environment variable `AUTO_SD_PAINT_EXT_AUTO_UPDATE` to `True`."
    )
    print("[auto-sd-paint-ext] Auto-update disabled by default for future versions.")
    print("[auto-sd-paint-ext] Please update using the Extensions Tab in A1111 WebUI.")
    print(
        "[auto-sd-paint-ext] See https://github.com/Interpause/auto-sd-paint-ext/issues/89 for further details."
    )

# NOTE: if we ever get dependencies, we can install them here.
