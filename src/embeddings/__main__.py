"""
CLI for managing Codex AOTGraph embeddings.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.embeddings import EmbeddingPipeline, HashEmbeddingClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Codex AOTGraph embeddings.")
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/embeddings.db"),
        help="Path to the SQLite database storing embeddings.",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        default=["Method", "Class", "Table", "Field"],
        help="Node labels to include when generating embeddings.",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="If provided, run a similarity search instead of generating embeddings.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of matches to return for similarity search.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    pipeline = EmbeddingPipeline.default(
        store_path=args.store,
        embedding_client=HashEmbeddingClient(),
    )
    try:
        if args.query:
            matches = pipeline.similarity_search(args.query, top_k=args.top_k)
            for match in matches:
                print(f"{match.score:.4f} {match.label} {match.node_id}")
                print(match.text)
                print("---")
        else:
            count = pipeline.run(labels=args.labels)
            print(f"Generated embeddings for {count} nodes.")
    finally:
        pipeline.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


