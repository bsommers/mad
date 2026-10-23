from mad.launch import build_command
from mad.route import Decision


def test_claude_argv():
    d = Decision("claude", "sonnet", ["kw:debug"], {"claude": 1, "agy": 0})
    assert build_command(d, "debug x", [], {}) == ["claude", "--model", "sonnet", "debug x"]


def test_agy_argv_uses_dash_i():
    d = Decision("agy", "gemini-4-argon-high", ["kw:design"], {"claude": 0, "agy": 1})
    assert build_command(d, "design y", ["a.py", "b.py"], {}) == [
        "agy",
        "--model",
        "gemini-4-argon-high",
        "-i",
        "design y\n\nFiles: a.py b.py",
    ]


def test_bin_override():
    d = Decision("agy", "gemini-3.8-flash-medium", ["override:agent"], {"claude": 0, "agy": 0})
    argv = build_command(d, "hello", [], {"MAD_AGY_BIN": "/tmp/stub"})
    assert argv[0] == "/tmp/stub"
