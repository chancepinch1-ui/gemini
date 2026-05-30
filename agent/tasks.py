"""Automation tasks.

Add your own work here: write a function that takes the AgentState
(so it can log) and returns a short human-readable detail string.
Register it with @task and the scheduler will run it every interval.
"""

import os
import shutil
import time
from typing import Callable, Dict

from .state import AgentState

TaskFn = Callable[[AgentState], str]

_REGISTRY: Dict[str, TaskFn] = {}


def task(name: str) -> Callable[[TaskFn], TaskFn]:
    def wrap(fn: TaskFn) -> TaskFn:
        _REGISTRY[name] = fn
        return fn

    return wrap


def registry() -> Dict[str, TaskFn]:
    return dict(_REGISTRY)


@task("heartbeat")
def heartbeat(state: AgentState) -> str:
    """Sample task: proves the background loop is alive and reports disk usage."""
    total, used, free = shutil.disk_usage(os.getcwd())
    pct = used / total * 100 if total else 0.0
    state.log(f"[heartbeat] disk {pct:.1f}% used, {free // (1024**3)} GiB free")
    return f"disk {pct:.1f}% used"


@task("uptime")
def uptime(state: AgentState) -> str:
    """Sample task: records a wall-clock tick."""
    now = time.strftime("%H:%M:%S")
    state.log(f"[uptime] tick at {now}")
    return f"tick {now}"
