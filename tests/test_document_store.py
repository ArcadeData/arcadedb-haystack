# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

"""
Integration tests for ArcadeDBDocumentStore.

Prerequisites:
    docker run -d -p 2480:2480 \
        -e JAVA_OPTS="-Darcadedb.server.rootPassword=arcadedb" \
        arcadedata/arcadedb:latest
"""

import os
import unittest

from haystack import Document
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.arcadedb import ArcadeDBDocumentStore


def _store(**kwargs) -> ArcadeDBDocumentStore:
    return ArcadeDBDocumentStore(
        url=os.getenv("ARCADEDB_URL", "http://localhost:2480"),
        database="haystack_test",
        username=kwargs.pop("username", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["username"],
        password=kwargs.pop("password", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["password"],
        recreate_type=True,
        **kwargs,
    )


def _sample_docs(n: int = 3, dim: int = 4) -> list[Document]:
    docs = []
    for i in range(n):
        docs.append(
            Document(
                content=f"Document number {i}",
                embedding=[float(i)] * dim,
                meta={"category": "test", "priority": i},
            )
        )
    return docs


class TestArcadeDBDocumentStore(unittest.TestCase):
    """Integration tests — require a running ArcadeDB instance."""

    def setUp(self):
        self.store = _store(embedding_dimension=4)

    # ---- count ----

    def test_count_empty(self):
        self.assertEqual(self.store.count_documents(), 0)

    def test_count_after_write(self):
        docs = _sample_docs(5)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
        self.assertEqual(self.store.count_documents(), 5)

    # ---- write ----

    def test_write_and_read(self):
        docs = _sample_docs(2)
        written = self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
        self.assertEqual(written, 2)

        all_docs = self.store.filter_documents()
        self.assertEqual(len(all_docs), 2)

    def test_write_overwrite(self):
        docs = _sample_docs(1)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        # Modify content and overwrite
        docs[0].content = "Updated content"
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        all_docs = self.store.filter_documents()
        self.assertEqual(len(all_docs), 1)
        self.assertEqual(all_docs[0].content, "Updated content")

    def test_write_skip(self):
        docs = _sample_docs(1)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        # Attempt to write same doc with SKIP policy
        written = self.store.write_documents(docs, policy=DuplicatePolicy.SKIP)
        self.assertEqual(written, 0)
        self.assertEqual(self.store.count_documents(), 1)

    def test_write_duplicate_raises(self):
        docs = _sample_docs(1)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        from haystack.document_stores.errors import DuplicateDocumentError

        with self.assertRaises(DuplicateDocumentError):
            self.store.write_documents(docs, policy=DuplicatePolicy.NONE)

    # ---- delete ----

    def test_delete(self):
        docs = _sample_docs(3)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        ids_to_delete = [docs[0].id, docs[1].id]
        self.store.delete_documents(ids_to_delete)

        self.assertEqual(self.store.count_documents(), 1)

    # ---- filter ----

    def test_filter_equality(self):
        docs = _sample_docs(3)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        result = self.store.filter_documents(
            filters={"field": "meta.category", "operator": "==", "value": "test"}
        )
        self.assertEqual(len(result), 3)

    def test_filter_comparison(self):
        docs = _sample_docs(5)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        result = self.store.filter_documents(
            filters={"field": "meta.priority", "operator": ">", "value": 2}
        )
        self.assertEqual(len(result), 2)  # priority 3 and 4

    def test_filter_and(self):
        docs = _sample_docs(5)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        result = self.store.filter_documents(
            filters={
                "operator": "AND",
                "conditions": [
                    {"field": "meta.category", "operator": "==", "value": "test"},
                    {"field": "meta.priority", "operator": ">=", "value": 3},
                ],
            }
        )
        self.assertEqual(len(result), 2)

    # ---- embedding retrieval ----

    def test_embedding_retrieval(self):
        docs = _sample_docs(5, dim=4)
        self.store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

        results = self.store._embedding_retrieval(
            query_embedding=[4.0, 4.0, 4.0, 4.0], top_k=3
        )
        self.assertLessEqual(len(results), 3)
        # The closest document should be the one with embedding [4.0, 4.0, 4.0, 4.0]
        self.assertIsNotNone(results[0].score)

    # ---- serialization ----

    def test_to_dict_from_dict(self):
        store = _store(embedding_dimension=4)
        data = store.to_dict()
        restored = ArcadeDBDocumentStore.from_dict(data)
        self.assertEqual(restored._database, store._database)
        self.assertEqual(restored._embedding_dimension, store._embedding_dimension)


if __name__ == "__main__":
    unittest.main()
