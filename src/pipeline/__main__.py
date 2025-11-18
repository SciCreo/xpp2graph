"""
Command line entry point for the Codex AOTGraph ingestion pipeline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.pipeline import IngestionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest Dynamics 365 F&O AOT XML exports into Neo4j."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more AOT XML files or directories containing XML exports.",
    )
    return parser


def expand_paths(inputs: list[Path]) -> list[Path]:
    resolved: list[Path] = []
    for input_path in inputs:
        if input_path.is_dir():
            resolved.extend(path for path in input_path.rglob("*.xml") if path.is_file())
        elif input_path.is_file():
            resolved.append(input_path)
        else:
            raise FileNotFoundError(f"{input_path} does not exist")
    if not resolved:
        raise RuntimeError("No XML files found for ingestion")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    xml_paths = expand_paths(args.paths)

    pipeline = IngestionPipeline()
    result = pipeline.ingest(xml_paths)

    print(
        f"Ingestion complete: {result.classes_processed} classes, "
        f"{result.methods_processed} methods, "
        f"{result.tables_processed} tables, "
        f"{result.fields_processed} fields."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


