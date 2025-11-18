"""
CLI for managing Codex AOTGraph embeddings.
"""

from __future__ import annotations

import argparse
from src.embeddings import EmbeddingPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Codex AOTGraph embeddings.")
    parser.add_argument(
        "--labels",
        nargs="*",
        default=["Method", "Class", "Table", "Field"],
        help="Node labels to include when generating embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of nodes to embed per API call.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline = EmbeddingPipeline.default()
    count = pipeline.run(labels=args.labels, batch_size=args.batch_size)
    print(f"Generated embeddings for {count} nodes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


