from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .. import __version__
from ..domain.context import BuildRequest
from ..domain.diagnostics import DiagnosticLevel
from ..domain.exit_codes import ExitCode
from ..infra.workspace import ROOT_ENV_VAR
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
            _print_diagnostics(exc.diagnostics, _json_mode(args))
            return exc.exit_code
        print(f"error: {exc}", file=sys.stderr)
        return ExitCode.INTERNAL_ERROR


def _add_root_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-r",
        "--root",
        dest="workspace_root",
        type=Path,
        metavar="PATH",
        help=f"Workspace root folder; takes precedence over {ROOT_ENV_VAR}",
    )


def _add_format_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format; json writes machine-readable output to stdout (default: text)",
    )


def _json_mode(args: argparse.Namespace) -> bool:
    return getattr(args, "format", "text") == "json"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ktisma",
        description="Portable LaTeX build toolkit.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"ktisma {__version__}"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(dest="command")

    # --- build ---
    build_parser = subparsers.add_parser("build", help="Build a LaTeX document")
    build_parser.add_argument("source", type=Path, help="Source .tex file")
    _add_root_option(build_parser)
    build_parser.add_argument("--engine", help="Override engine selection")
    build_parser.add_argument("-o", "--output", type=Path, help="Override output PDF path")
    build_parser.add_argument("--output-dir", type=Path, help="Override output directory")
    build_parser.add_argument("--watch", action="store_true", help="Enable watch mode")
    build_parser.add_argument("--dry-run", action="store_true", help="Show plan without building")
    build_parser.add_argument("--variant", help="Build a specific variant")
    build_parser.add_argument("--variant-payload", help="Explicit variant TeX payload")
    build_parser.add_argument(
        "--cleanup", choices=["never", "on_success", "on_output_success", "always"]
    )
    _add_format_option(build_parser)
    build_parser.set_defaults(func=_cmd_build)

    # --- inspect ---
    inspect_parser = subparsers.add_parser("inspect", help="Inspect build decisions")
    inspect_sub = inspect_parser.add_subparsers(dest="inspect_command")

    inspect_engine = inspect_sub.add_parser("engine", help="Inspect engine selection")
    inspect_engine.add_argument("source", type=Path, help="Source .tex file")
    _add_root_option(inspect_engine)
    inspect_engine.add_argument("--engine", help="Override engine")
    _add_format_option(inspect_engine)
    inspect_engine.set_defaults(func=_cmd_inspect_engine)

    inspect_route = inspect_sub.add_parser("route", help="Inspect output routing")
    inspect_route.add_argument("source", type=Path, help="Source .tex file")
    _add_root_option(inspect_route)
    inspect_route.add_argument("-o", "--output", type=Path)
    inspect_route.add_argument("--output-dir", type=Path)
    _add_format_option(inspect_route)
    inspect_route.set_defaults(func=_cmd_inspect_route)

    # --- clean ---
    clean_parser = subparsers.add_parser("clean", help="Clean build directories")
    clean_parser.add_argument("target", type=Path, help="Source .tex file or build directory")
    _add_root_option(clean_parser)
    clean_parser.set_defaults(func=_cmd_clean)

    # --- check-log ---
    check_log_parser = subparsers.add_parser(
        "check-log", help="Check retained LaTeX build logs against a zero baseline"
    )
    check_log_parser.add_argument("source_dir", type=Path, help="Directory holding the sources")
    check_log_parser.add_argument("stem", nargs="?", help="Restrict the check to one document stem")
    check_log_parser.add_argument(
        "--build-dir",
        default=".ktisma_build",
        help="Build directory relative to the source directory",
    )
    check_log_parser.add_argument(
        "--channel",
        action="append",
        default=[],
        metavar="TAGS",
        help="Report comma-separated measurement channels; may be repeated",
    )
    check_log_parser.set_defaults(func=_cmd_check_log)

    # --- doctor ---
    doctor_parser = subparsers.add_parser("doctor", help="Check prerequisites")
    _add_root_option(doctor_parser)
    _add_format_option(doctor_parser)
    doctor_parser.set_defaults(func=_cmd_doctor)

    # --- batch ---
    batch_parser = subparsers.add_parser("batch", help="Build all .tex files in a directory")
    batch_parser.add_argument("source_dir", type=Path, help="Directory containing .tex files")
    _add_root_option(batch_parser)
    batch_parser.add_argument("--engine", help="Override engine")
    batch_parser.add_argument("--watch", action="store_true")
    _add_format_option(batch_parser)
    batch_parser.set_defaults(func=_cmd_batch)

    # --- variants ---
    variants_parser = subparsers.add_parser("variants", help="Build all configured variants")
    variants_parser.add_argument("source", type=Path, help="Source .tex file")
    _add_root_option(variants_parser)
    variants_parser.add_argument("--engine", help="Override engine")
    variants_parser.add_argument(
        "--include-default",
        action="store_true",
        help="Also build the non-variant output alongside configured variants",
    )
    _add_format_option(variants_parser)
    variants_parser.set_defaults(func=_cmd_variants)

    # --- init ---
    init_parser = subparsers.add_parser(
        "init", help="Generate wrapper script and editor configuration"
    )
    _add_root_option(init_parser)
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing wrapper script, which may hold edits of the researcher",
    )
    init_parser.set_defaults(func=_cmd_init)

    # --- tex ---
    tex_parser = subparsers.add_parser("tex", help="Manage declared TeX dependencies")
    tex_sub = tex_parser.add_subparsers(dest="tex_command")
    for name, help_text, handler in (
        (
            "install",
            "Install and select the declared dependency snapshot",
            _cmd_tex_install,
        ),
        ("check", "Validate the selected dependency snapshot", _cmd_tex_check),
        ("inspect", "Inspect the selected dependency snapshot", _cmd_tex_inspect),
    ):
        command = tex_sub.add_parser(name, help=help_text)
        _add_root_option(command)
        _add_format_option(command)
        command.set_defaults(func=handler)
    resolve = tex_sub.add_parser(
        "resolve", help="Resolve one declared entry point from the selected snapshot"
    )
    resolve.add_argument("reference", help="qualified entry point, DEPENDENCY:ENTRYPOINT")
    _add_root_option(resolve)
    _add_format_option(resolve)
    resolve.set_defaults(func=_cmd_tex_resolve)

    return parser


def _cmd_build(args: argparse.Namespace) -> int:
    request = BuildRequest(
        watch=args.watch,
        dry_run=args.dry_run,
        engine_override=args.engine,
        output_path_override=(args.output.expanduser().resolve() if args.output else None),
        output_dir_override=(args.output_dir.expanduser().resolve() if args.output_dir else None),
        variant=args.variant,
        variant_payload=(args.variant_payload if hasattr(args, "variant_payload") else None),
        json_output=_json_mode(args),
        cleanup_override=args.cleanup,
    )

    result = bootstrap.build(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, _json_mode(args))

    if _json_mode(args):
        source_file = args.source.expanduser().resolve()
        _print_json(_build_result_to_dict(result, source_file))
    elif result.exit_code == ExitCode.SUCCESS and result.produced_paths:
        for p in result.produced_paths:
            print(p)
    elif result.backend_result is not None:
        _print_backend_streams(result.backend_result)

    return result.exit_code


def _cmd_inspect_engine(args: argparse.Namespace) -> int:
    request = BuildRequest(engine_override=args.engine, json_output=_json_mode(args))

    decision = bootstrap.inspect_engine_cmd(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    if _json_mode(args):
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
        output_path_override=(args.output.expanduser().resolve() if args.output else None),
        output_dir_override=(args.output_dir.expanduser().resolve() if args.output_dir else None),
        json_output=_json_mode(args),
    )

    decision = bootstrap.inspect_route_cmd(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    if _json_mode(args):
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


def _cmd_check_log(args: argparse.Namespace) -> int:
    channels = tuple(
        channel
        for group in args.channel
        for channel in (item.strip() for item in group.split(","))
        if channel
    )
    result = bootstrap.check_log(
        source_dir=args.source_dir,
        build_dir_name=args.build_dir,
        stem=args.stem,
        channels=channels,
    )
    _print_diagnostics(result.diagnostics, False)
    if result.diagnostics:
        return result.exit_code

    for report in result.reports:
        print(f"\n=== {report.relative_path} ===")
        for finding in report.evaluation.findings:
            if finding.count:
                print(f"  FAIL  {finding.count} x {finding.name}")
        if report.evaluation.output_line is None:
            print("  FAIL  no PDF written")
        else:
            print(f"  ok    {report.evaluation.output_line}")
        for line in report.evaluation.channel_lines:
            print(f"  {line}")

    verdict = (
        "zero baseline holds." if result.exit_code == ExitCode.SUCCESS else "BASELINE VIOLATED."
    )
    print(f"\n{verdict}")
    return result.exit_code


def _cmd_doctor(args: argparse.Namespace) -> int:
    result = bootstrap.doctor(workspace_root=args.workspace_root)

    if _json_mode(args):
        _print_json(
            {
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
            }
        )
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
        json_output=_json_mode(args),
    )

    result = bootstrap.batch(
        source_dir=args.source_dir,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, _json_mode(args))

    if _json_mode(args):
        _print_json(
            {
                "exit_code": int(result.exit_code),
                "results": [
                    {"source": str(p), "build": _build_result_to_dict(r, p)}
                    for p, r in result.results
                ],
                "diagnostics": [d.to_dict() for d in result.diagnostics],
            }
        )

    return result.exit_code


def _cmd_init(args: argparse.Namespace) -> int:
    from .init import execute_init
    from ..infra.workspace import resolve_workspace_root

    workspace_root = resolve_workspace_root(cli_workspace_root=args.workspace_root)
    return execute_init(workspace_root, force=args.force)


def _cmd_variants(args: argparse.Namespace) -> int:
    request = BuildRequest(
        engine_override=args.engine,
        include_default=args.include_default,
        json_output=_json_mode(args),
    )

    result = bootstrap.variants(
        source_file=args.source,
        request=request,
        workspace_root=args.workspace_root,
    )

    _print_diagnostics(result.diagnostics, _json_mode(args))

    if _json_mode(args):
        _print_json(
            {
                "exit_code": int(result.exit_code),
                "variants": [
                    {
                        "name": v.name,
                        "build": _build_result_to_dict(r, args.source.expanduser().resolve()),
                    }
                    for v, r in result.results
                ],
                "diagnostics": [d.to_dict() for d in result.diagnostics],
            }
        )

    return result.exit_code


def _cmd_tex_install(args: argparse.Namespace) -> int:
    return _render_tex_result(bootstrap.tex_install(args.workspace_root), _json_mode(args))


def _cmd_tex_check(args: argparse.Namespace) -> int:
    return _render_tex_result(bootstrap.tex_check(args.workspace_root), _json_mode(args))


def _cmd_tex_inspect(args: argparse.Namespace) -> int:
    return _render_tex_result(bootstrap.tex_inspect(args.workspace_root), _json_mode(args))


def _cmd_tex_resolve(args: argparse.Namespace) -> int:
    result = bootstrap.tex_resolve(args.reference, args.workspace_root)
    _print_diagnostics(result.diagnostics, _json_mode(args))
    if _json_mode(args):
        _print_json(
            {
                "exit_code": int(result.exit_code),
                "reference": result.reference,
                "path": str(result.path) if result.path else None,
                "record_digest": result.record_digest,
                "diagnostics": [diagnostic.to_dict() for diagnostic in result.diagnostics],
            }
        )
    elif result.path is not None:
        print(result.path)
    return result.exit_code


def _render_tex_result(result, use_json: bool) -> int:
    _print_diagnostics(result.diagnostics, use_json)
    data = {
        "exit_code": int(result.exit_code),
        "record_digest": result.record_digest,
        "texmf_root": str(result.texmf_root) if result.texmf_root else None,
        "receipt": result.receipt.to_dict() if result.receipt else None,
        "declared_dependencies": [
            {
                "name": dependency.name,
                "repository": dependency.repository,
                "commit": dependency.commit,
                "builder": dependency.builder,
                "provides": list(dependency.provides),
            }
            for dependency in result.declared_dependencies
        ],
        "resolved_entrypoints": {
            key: str(path) for key, path in sorted(result.resolved_entrypoints.items())
        },
        "diagnostics": [diagnostic.to_dict() for diagnostic in result.diagnostics],
    }
    if use_json:
        _print_json(data)
    else:
        if result.record_digest:
            print(f"Record: {result.record_digest}")
        if result.texmf_root:
            print(f"TEXMFHOME: {result.texmf_root}")
        for entrypoint, path in sorted(result.resolved_entrypoints.items()):
            print(f"{entrypoint}: {path}")
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


def _build_result_to_dict(result, source_file: Path) -> dict:
    return {
        "exit_code": int(result.exit_code),
        "engine": result.engine.to_dict() if result.engine else None,
        "route": result.route.to_dict(source_file) if result.route else None,
        "build_plan": result.build_plan.to_dict() if result.build_plan else None,
        "backend_result": _backend_result_to_dict(result.backend_result),
        "produced_paths": [str(p) for p in result.produced_paths],
        "diagnostics": [d.to_dict() for d in result.diagnostics],
    }


def _backend_result_to_dict(result) -> Optional[dict]:
    if result is None:
        return None
    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "pdf_path": str(result.pdf_path) if result.pdf_path else None,
        "diagnostics": [d.to_dict() for d in result.diagnostics],
    }


def _print_backend_streams(result) -> None:
    if result.stderr:
        print(
            result.stderr,
            file=sys.stderr,
            end="" if result.stderr.endswith("\n") else "\n",
        )
    if result.stdout:
        print(
            result.stdout,
            file=sys.stderr,
            end="" if result.stdout.endswith("\n") else "\n",
        )
