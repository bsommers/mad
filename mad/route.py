"""Routing: decide which agent and model should handle a prompt."""
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


def load_config(path: Path | None = None) -> dict:
    if path is None:
        env = os.environ.get("MAD_CONFIG")
        path = Path(env) if env else Path(__file__).resolve().parent.parent / "config" / "routing.json"
    return json.loads(Path(path).read_text())


@dataclass(frozen=True)
class Decision:
    agent: str
    model: str
    reasons: list[str]
    scores: dict[str, int]

    def to_json(self) -> str:
        return json.dumps(asdict(self))


def _hits(prompt: str, phrases: Sequence[str]) -> list[str]:
    text = prompt.lower()
    return [p for p in phrases if re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", text)]


def classify(prompt: str, files: Sequence[str], config: dict, agent: str | None = None,
             model: str | None = None) -> Decision:
    claude_hits = _hits(prompt, config["claude_keywords"])
    agy_hits = _hits(prompt, config["agy_keywords"])
    threshold = config["agy_file_threshold"]
    many_files = len(files) > threshold
    claude_score = len(claude_hits)
    agy_score = len(agy_hits) + (1 if many_files else 0)

    reasons = [f"kw:{p}" for p in claude_hits + agy_hits]
    if many_files:
        reasons.append(f"files:{len(files)}>{threshold}")
    opus_hits = _hits(prompt, config["opus_keywords"])
    haiku_hits = _hits(prompt, config["haiku_keywords"])
    for p in opus_hits + haiku_hits:
        if f"kw:{p}" not in reasons:
            reasons.append(f"kw:{p}")
    if agent:
        reasons.append("override:agent")
    if model:
        reasons.append("override:model")
    if not reasons:
        reasons = ["default"]

    chosen = agent or ("agy" if agy_score > claude_score else "claude")
    models = config["models"][chosen]
    if model:
        chosen_model = model
    elif chosen == "claude":
        if opus_hits:
            chosen_model = models["deep"]
        elif haiku_hits and claude_score == 0:
            chosen_model = models["light"]
        else:
            chosen_model = models["default"]
    else:
        chosen_model = models["light"] if agy_score == 0 else models["heavy"]

    return Decision(chosen, chosen_model, reasons, {"claude": claude_score, "agy": agy_score})
