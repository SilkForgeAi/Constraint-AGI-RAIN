"""Tests for RAG tool — add_document, query_rag."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.mock_vector import InMemoryRAGCollection


class TestRAG(unittest.TestCase):
    def test_add_and_query_rag(self) -> None:
        """Add document, query retrieves it (uses in-memory mock when Chroma not available)."""
        coll = InMemoryRAGCollection()
        with patch("rain.tools.rag._get_rag_collection", return_value=coll):
            with tempfile.TemporaryDirectory() as d:
                base = Path(d)
                from rain.tools.rag import add_document, query_rag

                doc_id = add_document("Rain is a cognitive system. It uses chain-of-thought.", source="README", base_path=base)
                self.assertTrue(doc_id.startswith("rag_"))

                results = query_rag("cognitive system", top_k=3, base_path=base)
                self.assertGreater(len(results), 0)
                self.assertIn("cognitive", results[0].get("content", ""))

    def test_query_empty_returns_empty(self) -> None:
        """Query on empty corpus returns empty (uses in-memory mock)."""
        coll = InMemoryRAGCollection()
        with patch("rain.tools.rag._get_rag_collection", return_value=coll):
            with tempfile.TemporaryDirectory() as d:
                base = Path(d)
                from rain.tools.rag import query_rag

                results = query_rag("anything", base_path=base)
                self.assertEqual(results, [])
