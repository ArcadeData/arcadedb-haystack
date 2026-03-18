# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for ArcadeDBDocumentStore (using testcontainers)."""

import pytest
from haystack import Document
from haystack.document_stores.errors import DuplicateDocumentError
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.arcadedb import ArcadeDBDocumentStore


def _store(arcadedb_url, **kwargs):
    return ArcadeDBDocumentStore(
        url=arcadedb_url,
        database="haystack_test",
        username=kwargs.pop("username", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["username"],
        password=kwargs.pop("password", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["password"],
        recreate_type=True,
        **kwargs,
    )


def _sample_docs(n=3, dim=4):
    return [
        Document(
            content=f"Document number {i}",
            embedding=[float(i)] * dim,
            meta={"category": "test", "priority": i},
        )
        for i in range(n)
    ]


# ---- count ----


def test_count_empty(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    assert store.count_documents() == 0


def test_count_after_write(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    assert store.count_documents() == 5


# ---- write ----


def test_write_and_read(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(2)
    written = store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    assert written == 2

    all_docs = store.filter_documents()
    assert len(all_docs) == 2


def test_write_overwrite(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    docs[0].content = "Updated content"
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    all_docs = store.filter_documents()
    assert len(all_docs) == 1
    assert all_docs[0].content == "Updated content"


def test_write_skip(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    written = store.write_documents(docs, policy=DuplicatePolicy.SKIP)
    assert written == 0
    assert store.count_documents() == 1


def test_write_duplicate_raises(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    with pytest.raises(DuplicateDocumentError):
        store.write_documents(docs, policy=DuplicatePolicy.NONE)


# ---- delete ----


def test_delete(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(3)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    store.delete_documents([docs[0].id, docs[1].id])
    assert store.count_documents() == 1


# ---- filter ----


def test_filter_equality(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(3)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={"field": "meta.category", "operator": "==", "value": "test"}
    )
    assert len(result) == 3


def test_filter_comparison(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={"field": "meta.priority", "operator": ">", "value": 2}
    )
    assert len(result) == 2


def test_filter_and(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={
            "operator": "AND",
            "conditions": [
                {"field": "meta.category", "operator": "==", "value": "test"},
                {"field": "meta.priority", "operator": ">=", "value": 3},
            ],
        }
    )
    assert len(result) == 2


# ---- embedding retrieval ----


def test_embedding_retrieval(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5, dim=4)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    results = store._embedding_retrieval(
        query_embedding=[4.0, 4.0, 4.0, 4.0], top_k=3
    )
    assert len(results) <= 3
    assert results[0].score is not None


# ---- serialization ----


def test_to_dict_from_dict(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    data = store.to_dict()
    restored = ArcadeDBDocumentStore.from_dict(data)
    assert restored._database == store._database
    assert restored._embedding_dimension == store._embedding_dimension
