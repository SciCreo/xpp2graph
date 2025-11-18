"""
Command line entry point for the Codex AOTGraph ingestion pipeline.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from src.pipeline import IngestionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest Dynamics 365 F&O AOT XML exports into Neo4j."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more AOT XML files, directories, or zip archives containing exports.",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        help="Optional directory used to extract zip archives. Defaults to a temporary folder.",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep extracted zip contents instead of deleting temporary directories.",
    )
    return parser


def resolve_inputs(
    inputs: Iterable[Path],
    *,
    staging_dir: Path | None = None,
    keep_extracted: bool = False,
) -> tuple[list[Path], list[Path]]:
    resolved: list[Path] = []
    temp_dirs: list[Path] = []

    if staging_dir is not None:
        staging_dir.mkdir(parents=True, exist_ok=True)

    for input_path in inputs:
        if input_path.is_dir():
            resolved.extend(path for path in input_path.rglob("*.xml") if path.is_file())
            continue

        if not input_path.exists():
            raise FileNotFoundError(f"{input_path} does not exist")

        if input_path.suffix.lower() == ".zip":
            extraction_root = _extract_archive(input_path, staging_dir)
            if not keep_extracted:
                temp_dirs.append(extraction_root)
            _log_descriptor_summary(extraction_root, input_path.name)
            resolved.extend(
                path
                for path in extraction_root.rglob("*.xml")
                if path.is_file() and "Descriptor" not in path.parts
            )
        else:
            resolved.append(input_path)

    if not resolved:
        raise RuntimeError("No XML files found for ingestion")

    # Deduplicate while preserving order
    ordered_unique: dict[Path, None] = {}
    for path in resolved:
        ordered_unique.setdefault(path, None)

    return list(ordered_unique.keys()), temp_dirs


def _extract_archive(archive_path: Path, staging_dir: Path | None) -> Path:
    target_dir = (
        Path(tempfile.mkdtemp(prefix="aotgraph_", dir=staging_dir))
        if staging_dir is None
        else Path(tempfile.mkdtemp(prefix="aotgraph_", dir=staging_dir))
    )
    with zipfile.ZipFile(archive_path) as zip_file:
        zip_file.extractall(target_dir)
    return target_dir


def _log_descriptor_summary(extraction_root: Path, archive_name: str) -> None:
    descriptor_files = list(extraction_root.glob("**/Descriptor/*.xml"))
    if not descriptor_files:
        print(f"[extract] {archive_name}: no descriptor found.")
        return

    descriptor_path = descriptor_files[0]
    try:
        tree = ET.parse(descriptor_path)
        root = tree.getroot()
    except ET.ParseError:
        print(f"[extract] {archive_name}: failed to parse descriptor at {descriptor_path}.")
        return

    name = root.findtext("Name") or descriptor_path.stem
    display_name = root.findtext("DisplayName") or name
    version = ".".join(
        filter(
            None,
            [
                root.findtext("VersionMajor"),
                root.findtext("VersionMinor"),
                root.findtext("VersionBuild"),
                root.findtext("VersionRevision"),
            ],
        )
    )
    module = root.findtext("ModelModule") or root.findtext("Model") or "Unknown"
    print(
        f"[extract] {archive_name}: model={name} display='{display_name}' "
        f"module={module} version={version or 'n/a'}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    xml_paths, temp_dirs = resolve_inputs(
        args.paths,
        staging_dir=args.staging_dir,
        keep_extracted=args.keep_extracted,
    )

    pipeline = IngestionPipeline()

    try:
        result = pipeline.ingest(xml_paths)
    finally:
        if not args.keep_extracted:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    print(
        f"Ingestion complete: {result.classes_processed} classes, "
        f"{result.methods_processed} methods, "
        f"{result.tables_processed} tables, "
        f"{result.fields_processed} fields."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

