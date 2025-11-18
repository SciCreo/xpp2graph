"""
Ingestion pipeline that converts AOT XML exports into the Neo4j knowledge graph.
"""

from .ingest import IngestionPipeline

__all__ = ["IngestionPipeline"]


