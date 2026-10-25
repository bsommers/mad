"""Usage telemetry estimator, atomic store, and limit evaluator (design §7)."""
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from mad.route import load_config
from mad.store import utc_iso


def _parse_iso_utc(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_user_prompt_entry(obj: dict[str, Any]) -> bool:
    if obj.get("type") != "user":
        return False
    if obj.get("isMeta"):
        return False
    msg = obj.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, list):
            if not content:
                return False
            if all(isinstance(block, dict) and block.get("type") == "tool_result" for block in content):
                return False
    return True


def count_claude_messages(
    transcripts_dir: Path,
    window_hours: float = 5.0,
    now: datetime | None = None,
) -> tuple[int, str | None]:
    """Count Claude user-prompt JSONL entries within the last `window_hours`."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current - timedelta(hours=window_hours)

    if not transcripts_dir.is_dir():
        return 0, None

    timestamps: list[datetime] = []
    for path in sorted(transcripts_dir.rglob("*.jsonl")):
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                for raw_line in fh:
                    if '"user"' not in raw_line:
                        continue
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict) or not _is_user_prompt_entry(obj):
                        continue
                    ts = _parse_iso_utc(obj.get("timestamp"))
                    if ts is not None and cutoff <= ts <= current:
                        timestamps.append(ts)
        except OSError:
            continue

    if not timestamps:
        return 0, None
    oldest = min(timestamps)
    return len(timestamps), utc_iso(oldest)


def read_telemetry(root: Path) -> dict[str, Any]:
    """Read `.agent_telemetry.json`, returning `{}` if missing or invalid."""
    path = root / ".agent_telemetry.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_telemetry_atomic(root: Path, data: Mapping[str, Any]) -> Path:
    """Atomically write `.agent_telemetry.json` via temp file + `os.replace`."""
    target = root / ".agent_telemetry.json"
    payload = json.dumps(data, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=root, prefix=".agent_telemetry.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, target)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return target


def check_limits(
    root: Path,
    cfg: Mapping[str, Any] | None = None,
    transcripts_dir: Path | None = None,
    record_rate_limit: bool = False,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Update `.agent_telemetry.json` and return `(should_handoff, telemetry_dict)`."""
    environ = env if env is not None else os.environ
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    config = cfg if cfg is not None else load_config()
    tcfg = config.get("telemetry", {}) if isinstance(config, Mapping) else {}

    window_hours = float(tcfg.get("window_hours", 5))
    budget = int(tcfg.get("window_message_budget", 45))
    ratio = float(tcfg.get("handoff_ratio", 0.8))
    max_concurrent = int(tcfg.get("agy_max_concurrent", 2))
    cooldown_minutes = float(tcfg.get("agy_rate_limit_cooldown_minutes", 15))

    if transcripts_dir is None:
        env_dir = environ.get("MAD_CLAUDE_PROJECTS_DIR")
        transcripts_dir = Path(env_dir) if env_dir else (Path.home() / ".claude" / "projects")

    messages_in_window, oldest_in_window = count_claude_messages(
        transcripts_dir, window_hours=window_hours, now=current
    )

    prev = read_telemetry(root)
    prev_agy = prev.get("agy") if isinstance(prev.get("agy"), dict) else {}

    raw_prev_running = prev_agy.get("running", 0)
    running = int(raw_prev_running) if isinstance(raw_prev_running, (int, float)) else 0
    env_running = environ.get("MAD_AGY_RUNNING", "").strip()
    if env_running:
        try:
            running = int(env_running)
        except ValueError as exc:
            raise ValueError(f"invalid MAD_AGY_RUNNING: {env_running}") from exc

    last_rate_limit: str | None = prev_agy.get("last_rate_limit")
    if record_rate_limit:
        last_rate_limit = utc_iso(current)

    data: dict[str, Any] = {
        "version": 1,
        "updated": utc_iso(current),
        "claude": {
            "window_hours": int(window_hours) if window_hours.is_integer() else window_hours,
            "window_message_budget": budget,
            "handoff_ratio": ratio,
            "messages_in_window": messages_in_window,
            "oldest_in_window": oldest_in_window,
        },
        "agy": {
            "max_concurrent": max_concurrent,
            "running": running,
            "last_rate_limit": last_rate_limit,
        },
    }
    write_telemetry_atomic(root, data)

    threshold = math.ceil(budget * ratio)
    rate_limited_recently = False
    rl_dt = _parse_iso_utc(last_rate_limit)
    if rl_dt is not None:
        rate_limited_recently = timedelta(0) <= (current - rl_dt) <= timedelta(minutes=cooldown_minutes)

    should_handoff = (
        environ.get("MAD_FORCE_HANDOFF") == "1"
        or messages_in_window >= threshold
        or running >= max_concurrent
        or rate_limited_recently
    )
    return should_handoff, data
