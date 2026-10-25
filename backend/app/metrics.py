"""Minimal in-process Prometheus-style metrics. Owner: ops.

Usage from any area:  metrics.inc("cybersafe_analyze_total", verdict="scam")
"""

import threading
from collections import defaultdict

_lock = threading.Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)


def inc(name: str, value: float = 1.0, **labels: str) -> None:
    key = (name, tuple(sorted((k, str(v)) for k, v in labels.items())))
    with _lock:
        _counters[key] += value


def render() -> str:
    lines: list[str] = []
    with _lock:
        items = sorted(_counters.items())
    for (name, labels), value in items:
        label_str = ",".join(f'{k}="{v}"' for k, v in labels)
        lines.append(f"{name}{{{label_str}}} {value}" if label_str else f"{name} {value}")
    return "\n".join(lines) + "\n"
