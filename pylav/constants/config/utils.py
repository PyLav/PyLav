from __future__ import annotations

import os
import pathlib


def _remove_keys(*keys, data: dict) -> dict:
    for key in keys:
        data.pop(key, None)
    return data


def in_container() -> bool:
    """Check if the current process is running in a container.

    Returns
    -------
    bool
        Whether or not the current process is running in a container.

    """
    try:
        proc_1 = r"/proc/1/sched"

        out = pathlib.Path(proc_1).read_text() if os.path.exists(proc_1) else ""
        checks = [
            "docker" in out,
            "/lxc/" in out,
            out.split(" ")[0]
            not in (
                "systemd",
                "init",
            )
            if out
            else False,
            os.path.exists("./dockerenv"),
            os.path.exists("/.dockerinit"),
            os.getenv("container") is not None,
        ]
        return any(checks)
    except Exception:
        return False
