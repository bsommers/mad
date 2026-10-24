"""Argparse CLI front end for mad."""
import argparse
import os
import shlex
import sys
from pathlib import Path

from mad.context import fetch_context, reindex_context
from mad.handoff import build_handoff_command, validate_handoff, write_handoff
from mad.launch import build_command, exec_command
from mad.route import classify, load_config
from mad.store import append_log, find_root, init_store
from mad.telemetry import check_limits


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mad")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_route = sub.add_parser("route")
    p_route.add_argument("--agent", choices=("claude", "agy"))
    p_route.add_argument("--model")
    p_route.add_argument("prompt")
    p_route.add_argument("files", nargs="*")

    p_run = sub.add_parser("run")
    p_run.add_argument("--agent", choices=("claude", "agy"))
    p_run.add_argument("--model")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("prompt")
    p_run.add_argument("files", nargs="*")

    p_log = sub.add_parser("log")
    p_log.add_argument("--kind", required=True)
    p_log.add_argument("--agent", required=True)
    p_log.add_argument("--field", action="append", default=[])
    p_log.add_argument("message")

    p_fetch = sub.add_parser("fetch")
    p_fetch.add_argument("--reindex", action="store_true")
    p_fetch.add_argument("--budget", type=int)
    p_fetch.add_argument("keywords", nargs="*")

    p_handoff = sub.add_parser("handoff")
    p_handoff.add_argument("--write", action="store_true")
    p_handoff.add_argument("--agent", choices=("claude", "agy", "human", "mad"))
    p_handoff.add_argument("--problem")
    p_handoff.add_argument("--step", action="append", default=[])
    p_handoff.add_argument("--context", action="append", default=[])
    p_handoff.add_argument("--verify", action="append", default=[])
    p_handoff.add_argument("--model")
    p_handoff.add_argument("--file")
    p_handoff.add_argument("--dry-run", action="store_true")

    p_check = sub.add_parser("check")
    p_check.add_argument("--transcripts-dir")
    p_check.add_argument("--record-rate-limit", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = find_root(Path.cwd())

    try:
        if ns.cmd == "init":
            created = init_store(root)
            if not created:
                print("nothing to do")
            else:
                for p in created:
                    print(p.relative_to(root))
            return 0

        if ns.cmd == "route":
            cfg = load_config()
            decision = classify(ns.prompt, ns.files, cfg, agent=ns.agent, model=ns.model)
            print(decision.to_json())
            return 0

        if ns.cmd == "run":
            cfg = load_config()
            decision = classify(ns.prompt, ns.files, cfg, agent=ns.agent, model=ns.model)
            cmd = build_command(decision, ns.prompt, ns.files, os.environ)
            if ns.dry_run:
                print(shlex.join(cmd))
                return 0
            append_log(
                root,
                "transition",
                decision.agent,
                {
                    "model": decision.model,
                    "task": ns.prompt,
                    "reasons": ",".join(decision.reasons),
                },
            )
            exec_command(cmd)

        if ns.cmd == "log":
            fields: dict[str, str] = {"task": ns.message}
            for item in ns.field:
                if "=" not in item:
                    parser.error(f"invalid --field (expected k=v): {item}")
                k, v = item.split("=", 1)
                if not k:
                    parser.error(f"invalid --field (empty key): {item}")
                fields[k] = v
            append_log(root, ns.kind, ns.agent, fields)
            return 0

        if ns.cmd == "fetch":
            if not ns.reindex and not ns.keywords:
                parser.error("fetch requires --reindex or at least one KEYWORD")
            if ns.reindex:
                idx = reindex_context(root)
                if not ns.keywords:
                    print(idx.relative_to(root))
                    return 0
            cfg = load_config()
            budget = ns.budget if ns.budget is not None else int(cfg.get("fetch_budget_bytes", 24000))
            for p in fetch_context(root, ns.keywords, budget_bytes=budget):
                print(p.relative_to(root))
            return 0

        if ns.cmd == "handoff":
            hpath = Path(ns.file) if ns.file else (root / ".opengsd_handoff.md")
            if ns.write:
                if not ns.agent or not ns.problem or not ns.step:
                    parser.error("handoff --write requires --agent, --problem, and at least one --step")
                out = write_handoff(
                    root,
                    agent=ns.agent,
                    problem=ns.problem,
                    steps=ns.step,
                    context_files=ns.context,
                    verify_cmds=ns.verify,
                    handoff_path=hpath,
                )
                print(out.relative_to(root) if out.is_relative_to(root) else out)
                return 0

            content = validate_handoff(hpath)
            cfg = load_config()
            model = ns.model or cfg["models"]["agy"]["heavy"]
            cmd = build_handoff_command(content, model, os.environ)
            if ns.dry_run:
                print(shlex.join(cmd))
                return 0
            exec_command(cmd)

        if ns.cmd == "check":
            cfg = load_config()
            tdir = Path(ns.transcripts_dir) if ns.transcripts_dir else None
            should_handoff, _ = check_limits(
                root,
                cfg=cfg,
                transcripts_dir=tdir,
                record_rate_limit=ns.record_rate_limit,
                env=os.environ,
            )
            if should_handoff:
                print("handoff")
                return 10
            print("ok")
            return 0

    except ValueError as exc:
        print(f"mad: {exc}", file=sys.stderr)
        return 1

    return 2
