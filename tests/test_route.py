import json

import pytest

from mad.route import classify, load_config

CASES = [
    # prompt, files, agent_override, model_override, expected (agent, model, reasons, scores)
    ("debug the mqtt reconnect", ["a.py"], None, None, ("claude", "sonnet", ["kw:debug"], {"claude": 1, "agy": 0})),
    ("design the UNS tree", [], None, None, ("agy", "gemini-4-argon-high", ["kw:design", "kw:uns"], {"claude": 0, "agy": 2})),
    ("update the parser", list("abcdef"), None, None, ("agy", "gemini-4-argon-high", ["files:6>5"], {"claude": 0, "agy": 1})),
    ("update the parser", list("abcde"), None, None, ("claude", "sonnet", ["default"], {"claude": 0, "agy": 0})),
    ("debug it", list("abcdef"), None, None, ("claude", "sonnet", ["kw:debug", "files:6>5"], {"claude": 1, "agy": 1})),
    ("fix the race condition in the pool", [], None, None, ("claude", "opus", ["kw:race condition"], {"claude": 0, "agy": 0})),
    ("write a regex for dates", [], None, None, ("claude", "haiku", ["kw:regex"], {"claude": 0, "agy": 0})),
    ("write tests for the regex", [], None, None, ("claude", "sonnet", ["kw:write tests", "kw:regex"], {"claude": 1, "agy": 0})),
    ("list the files", [], "agy", None, ("agy", "gemini-3.8-flash-medium", ["override:agent"], {"claude": 0, "agy": 0})),
    ("debug x", [], None, "opus", ("claude", "opus", ["kw:debug", "override:model"], {"claude": 1, "agy": 0})),
    ("redesign the unsafe block", [], None, None, ("claude", "sonnet", ["default"], {"claude": 0, "agy": 0})),
    ("design x", [], None, "gemini-3.8-flash-medium", ("agy", "gemini-3.8-flash-medium", ["kw:design", "override:model"], {"claude": 0, "agy": 1})),
]


@pytest.mark.parametrize("prompt,files,agent,model,expected", CASES)
def test_classify(prompt, files, agent, model, expected):
    d = classify(prompt, files, load_config(), agent=agent, model=model)
    assert (d.agent, d.model, d.reasons, d.scores) == expected


def test_to_json_roundtrip():
    d = classify("debug x", [], load_config())
    assert json.loads(d.to_json()) == {"agent": "claude", "model": "sonnet", "reasons": ["kw:debug"], "scores": {"claude": 1, "agy": 0}}
