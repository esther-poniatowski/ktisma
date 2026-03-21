from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ..domain.context import BuildRequest
from ..domain.diagnostics import DiagnosticLevel
from ..domain.exit_codes import ExitCode
from . import bootstrap
from .log import format_diagnostics, setup_logging


def main(argv: Optional[list[str]] = None) -> int:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return ExitCode.CONFIG_ERROR

    setup_logging(verbose=getattr(args, "verbose", False))

    try:
        return args.func(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else ExitCode.INTERNAL_ERROR
    except Exception as exc:
        from ..domain.errors import KtismaError

        if isinstance(exc, KtismaError):
            _print_diagnostics(exc.diagnostics, getattr(args, "json", False))
            return exc.exit_code
        print(f"error: {exc}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ktisma",
        description="Portable LaTeX build toolkit.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command")

    # --- build ---
    build_parser = subparsers.add_parser("build", help="Build a LaTeX document")
    build_parser.add_argument("source", type=Path, help="Source .tex file")
    build_parser.add_argument("--workspace-root", type=Path, help="Workspace root directory")
    build_parser.add_argument("--engine", help="Override engine selection")
    build_parser.add_argument("--output-dir", type=Path, help="Override output directory")
    build_parser.add_argument("--watch", action="store_true", help="Enable watch mode")
    build_parser.add_argument("--dry-run", action="store_true", help="Show plan without building")
    build_parser.add_argument("--variant", help="Build a specific variant")
    build_parser.add_argument("--variant-payload", help="Explicit variant TeX payload")
    build_parser.add_argument("--cleanup", choices=["never", "on_success", "on_output_success", "always"])
    build_parser.add_argument("--json", action="store_true", help="JSON output")
    build_parser.set_defaults(func=_cmd_build)

    # --- inspect ---
    inspect_parser = subparsers.add_parser("inspect", help="Inspect build decisions")
    inspect_sub = inspect_parser.add_subparsers(dest="inspect_command")

    inspect_engine = inspect_sub.add_parser("engine", help="Inspect engine selection")
    inspect_engine.add_argument("source", type=Path, help="Source .tex file")
    inspect_engine.add_argument("--workspace-root", type=Path)
    inspect_engine.add_argument("--engine", help="Override engine")
    inspect_engine.add_argument("--json", action="store_true")
    inspect_engine.set_defaults(func=_cmd_inspect_engine)

    inspect_route = inspect_sub.add_parser("route", help="Inspect output routing")
    inspect_route.add_argument("source", type=Path, help="Source .tex file")
    inspect_route.add_argument("--workspace-root", type=Path)
    inspect_route.add_argument("--output-dir", type=Path)
    inspect_route.add_argument("--json", action="store_true")
    inspect_route.set_defaults(func=_cmd_inspect_route)

    # --- clean ---
    clean_parser = subparsers.add_parser("clean", help="Clean build directories")
    clean_parser.add_argument("target", type=Path, help="Source .tex file or build directory")
    clean_parser.add_argument("--workspace-root", type=Path)
    clean_parser.set_defaults(func=_cmd_clean)

    # --- doctor ---
    doctor_parser = subparsers.add_parser("doctor", help="Check prerequisites")
    doctor_parser.add_argument("--workspace-root", type=Path)
    doctor_parser.add_argument("--json", action="store_true")
    doctor_parser.set_defaults(func=_cmd_doctor)

    # --- batch ---
    batch_parser = subparsers.add_parser("batch", help="Build all .tex files in a directory")
    batch_parser.add_argument("source_dir", type=Path, help="Directory containing .tex files")
    batch_parser.add_argument("--workspace-root", type=Path)
    batch_parser.add_argument("--engine", help="Override engine")
    batch_parser.add_argument("--watch", action="store_true")
    batch_parser.add_argument("--json", action="store_true")
    batch_parser.set_defaults(func=_cmd_batch)

    # --- variants ---
    variants_parser = subparsers.add_parser("variants", help="Build all configured variants")
    variants_parser.add_argument("source", type=Path, help="Source .tex file")
    variants_parser.add_argument("--workspace-root", type=Path)
    variants_parser.add_argument("--engine", help="Override engine")
    variants_parser.add_argument("--json", action="store_true")
    variants_parser.set_defaults(func=_cmd_variants)

    return parser


def _cmd_build(args: argparse.Namespace) -> int:
    request = BuildRequest(
        watch=args.watch,
        dry_run=args.dry_run,
        engine_override=args.engine,
        output_dir_override=args.output_dir.expanduser().resolve() if args.output_dir else None,
        variant=args.variant,
        variant_payload=args.variant_payload if hasattr(args, "variant_payload") else None,
        json_output=args.json,
        cleanup_override=args.cleanup,
    )

    result = bootstrap.build(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, args.json)

    if args.json:
        source_file = args.source.expanduser().resolve()
        _print_json({
            "exit_code": int(result.exit_code),
            "engine": result.engine.to_dict() if result.engine else None,
            "route": result.route.to_dict(source_file) if result.route else None,
            "build_plan": result.build_plan.to_dict() if result.build_plan else None,
            "produced_paths": [str(p) for p in result.produced_paths],
        })
    elif result.exit_code == ExitCode.SUCCESS and result.produced_paths:
        for p in result.produced_paths:
            print(p)

    return result.exit_code


def _cmd_inspect_engine(args: argparse.Namespace) -> int:
    request = BuildRequest(engine_override=args.engine, json_output=args.json)

    decision = bootstrap.inspect_engine_cmd(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    if args.json:
        _print_json(decision.to_dict())
    else:
        _print_diagnostics(decision.diagnostics, False)
        print(f"Engine: {decision.engine}")
        if decision.evidence:
            for e in decision.evidence:
                print(f"  {e}")
        if decision.ambiguous:
            print("  (ambiguous)")

    if any(d.level == DiagnosticLevel.ERROR for d in decision.diagnostics):
        return ExitCode.CONFIG_ERROR
    return ExitCode.SUCCESS


def _cmd_inspect_route(args: argparse.Namespace) -> int:
    request = BuildRequest(
        output_dir_override=args.output_dir.expanduser().resolve() if args.output_dir else None,
        json_output=args.json,
    )

    decision = bootstrap.inspect_route_cmd(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    if args.json:
        _print_json(decision.to_dict(args.source))
    else:
        _print_diagnostics(decision.diagnostics, False)
        print(f"Destination: {decision.destination}")
        if decision.matched_rule:
            print(f"  Matched rule: {decision.matched_rule}")
        if decision.fallback:
            print("  (fallback routing)")

    return ExitCode.SUCCESS


def _cmd_clean(args: argparse.Namespace) -> int:
    result = bootstrap.clean(
        target=args.target,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, False)

    if result.removed_dirs:
        for d in result.removed_dirs:
            print(f"Removed: {d}")

    return result.exit_code


def _cmd_doctor(args: argparse.Namespace) -> int:
    result = bootstrap.doctor(workspace_root=args.workspace_root)

    if args.json:
        _print_json({
            "exit_code": int(result.exit_code),
            "checks": [
                {
                    "name": c.name,
                    "available": c.available,
                    "version": c.version,
                    "message": c.message,
                }
                for c in result.checks
            ],
            "diagnostics": [d.to_dict() for d in result.diagnostics],
        })
    else:
        for check in result.checks:
            status = "ok" if check.available else "MISSING"
            print(f"  [{status}] {check.name}: {check.message}")
        _print_diagnostics(result.diagnostics, False)

    return result.exit_code


def _cmd_batch(args: argparse.Namespace) -> int:
    request = BuildRequest(
        watch=args.watch,
        engine_override=args.engine,
        json_output=args.json,
    )

    result = bootstrap.batch(
        source_dir=args.source_dir,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, args.json)

    if args.json:
        _print_json({
            "exit_code": int(result.exit_code),
            "results": [
                {"source": str(p), "exit_code": int(r.exit_code)}
                for p, r in result.results
            ],
            "diagnostics": [d.to_dict() for d in result.diagnostics],
        })

    return result.exit_code


def _cmd_variants(args: argparse.Namespace) -> int:
    request = BuildRequest(
        engine_override=args.engine,
        json_output=args.json,
    )

    result = bootstrap.variants(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, args.json)

    if args.json:
        _print_json({
            "exit_code": int(result.exit_code),
            "variants": [
                {"name": v.name, "exit_code": int(r.exit_code)}
                for v, r in result.results
            ],
            "diagnostics": [d.to_dict() for d in result.diagnostics],
        })

    return result.exit_code


def _print_diagnostics(diagnostics: list, use_json: bool) -> None:
    """Print diagnostics to stderr (human) or skip for JSON mode."""
    if use_json or not diagnostics:
        return
    output = format_diagnostics(diagnostics, use_color=sys.stderr.isatty())
    if output:
        print(output, file=sys.stderr)


def _print_json(data: dict) -> None:
    """Print JSON to stdout. Adapters must not mix human formatting into JSON output."""
    json.dump(data, sys.stdout, indent=2, default=str)
    print()
