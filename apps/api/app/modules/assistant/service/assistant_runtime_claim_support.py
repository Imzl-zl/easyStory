from __future__ import annotations

import os
import socket
from typing import Any, Literal
import uuid

from app.shared.runtime.errors import ConfigurationError

AssistantRuntimeClaimState = Literal["current_process", "active_other_process", "stale", "unknown"]
ASSISTANT_RUNTIME_CLAIM_KEYS = frozenset({"host", "instance_id", "pid"})
_CURRENT_RUNTIME_INSTANCE_ID = str(uuid.uuid4())
_CURRENT_RUNTIME_HOST = socket.gethostname().strip() or "unknown"
_CURRENT_RUNTIME_PID = os.getpid()


def build_current_runtime_claim_snapshot() -> dict[str, Any]:
    return {
        "host": _CURRENT_RUNTIME_HOST,
        "instance_id": _CURRENT_RUNTIME_INSTANCE_ID,
        "pid": _CURRENT_RUNTIME_PID,
    }


def normalize_runtime_claim_snapshot(
    snapshot: dict[str, Any],
    *,
    field_ref: str,
    path: str,
) -> dict[str, Any]:
    unknown_keys = set(snapshot) - ASSISTANT_RUNTIME_CLAIM_KEYS
    if unknown_keys:
        unknown_list = ", ".join(sorted(unknown_keys))
        raise ConfigurationError(f"{field_ref} contains unknown keys [{unknown_list}]: {path}")
    host = snapshot.get("host")
    instance_id = snapshot.get("instance_id")
    pid = snapshot.get("pid")
    if not isinstance(host, str) or not host.strip():
        raise ConfigurationError(f"{field_ref} must include non-empty host: {path}")
    if not isinstance(instance_id, str) or not instance_id.strip():
        raise ConfigurationError(f"{field_ref} must include non-empty instance_id: {path}")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        raise ConfigurationError(f"{field_ref} must include positive integer pid: {path}")
    return {
        "host": host.strip(),
        "instance_id": instance_id.strip(),
        "pid": pid,
    }


def resolve_runtime_claim_state(
    runtime_claim_snapshot: dict[str, Any] | None,
) -> AssistantRuntimeClaimState:
    if runtime_claim_snapshot is None:
        return "unknown"
    host = runtime_claim_snapshot.get("host")
    instance_id = runtime_claim_snapshot.get("instance_id")
    pid = runtime_claim_snapshot.get("pid")
    if host != _CURRENT_RUNTIME_HOST:
        return "unknown"
    if pid == _CURRENT_RUNTIME_PID and instance_id == _CURRENT_RUNTIME_INSTANCE_ID:
        return "current_process"
    if _is_process_alive(pid):
        return "active_other_process"
    return "stale"


def _is_process_alive(pid: object) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
        return False
    if pid == _CURRENT_RUNTIME_PID:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True
