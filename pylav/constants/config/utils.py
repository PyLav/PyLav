from __future__ import annotations

import os


def remove_keys(*keys, data: dict) -> dict:
    for key in keys:
        data.pop(key, None)
    return data


def in_container() -> bool:
    try:
        proc_1 = r"/proc/1/sched"

        if os.path.exists(proc_1):
            with open(proc_1) as fp:
                out = fp.read()
        else:
            out = ""

        checks = [
            "docker" in out,
            "/lxc/" in out,
            out.split(" ")[0]
            not in (
                "systemd",
                "init",
            ),
            os.path.exists("./dockerenv"),
            os.path.exists("/.dockerinit"),
            os.getenv("container") is not None,
        ]
        return any(checks)
    except Exception:
        return False
