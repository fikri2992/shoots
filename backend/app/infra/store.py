"""Document storage behind one small interface, including atomic conditions.

Two real implementations, not a mock and a real one:

* ``InMemoryStore`` — a genuine store with real query and ordering semantics. Runs
  the test suite and local development.
* ``FirestoreStore`` — production.

Both are exercised by the same contract tests (``tests/test_store_and_bus.py``), so
a behavioural difference between them is a test failure rather than a surprise in
production. This is what AGENTS.md means by no mocked repositories: nothing here
pretends to store something and then asserts it was asked to.
"""

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

Document = dict[str, Any]
Transform = Callable[[Document], Document | None]


@runtime_checkable
class Store(Protocol):
    async def put(self, collection: str, doc_id: str, data: Document) -> None: ...

    async def get(self, collection: str, doc_id: str) -> Document | None: ...

    async def query(
        self,
        collection: str,
        where: Document | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> list[Document]: ...

    async def delete(self, collection: str, doc_id: str) -> None: ...

    async def create(self, collection: str, doc_id: str, data: Document) -> bool: ...

    async def create_claimed(
        self,
        claim_collection: str,
        claim_id: str,
        claim: Document,
        collection: str,
        doc_id: str,
        data: Document,
    ) -> bool: ...

    async def delete_if(self, collection: str, doc_id: str, where: Document) -> bool: ...

    async def patch_if(
        self, collection: str, doc_id: str, changes: Document, where: Document
    ) -> bool: ...

    async def mutate(
        self, collection: str, doc_id: str, transform: Transform
    ) -> tuple[Document | None, bool]: ...


def _matches(document: Document, where: Document) -> bool:
    for field, expected in where.items():
        actual = document.get(field)
        # A list-valued field matches if it contains the expected value, mirroring
        # Firestore's array-contains. Used for project membership lookups.
        if isinstance(actual, list) and not isinstance(expected, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


class InMemoryStore:
    """Real storage semantics, held in a dict. Deep-copies on the way in and out so
    callers cannot mutate stored state by holding on to a reference."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Document]] = {}
        self._lock = asyncio.Lock()

    async def put(self, collection: str, doc_id: str, data: Document) -> None:
        async with self._lock:
            self._data.setdefault(collection, {})[doc_id] = _clone(data)

    async def get(self, collection: str, doc_id: str) -> Document | None:
        found = self._data.get(collection, {}).get(doc_id)
        return _clone(found) if found is not None else None

    async def query(
        self,
        collection: str,
        where: Document | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> list[Document]:
        results = [
            _clone(document)
            for document in self._data.get(collection, {}).values()
            if _matches(document, where or {})
        ]
        if order_by:
            results.sort(key=lambda d: _sort_key(d.get(order_by)), reverse=descending)
        return results[:limit] if limit is not None else results

    async def delete(self, collection: str, doc_id: str) -> None:
        async with self._lock:
            self._data.get(collection, {}).pop(doc_id, None)

    async def create(self, collection: str, doc_id: str, data: Document) -> bool:
        """Insert only when absent. The boolean is the storage-level claim."""
        async with self._lock:
            documents = self._data.setdefault(collection, {})
            if doc_id in documents:
                return False
            documents[doc_id] = _clone(data)
            return True

    async def create_claimed(
        self,
        claim_collection: str,
        claim_id: str,
        claim: Document,
        collection: str,
        doc_id: str,
        data: Document,
    ) -> bool:
        """Create a uniqueness claim and its document as one operation."""
        async with self._lock:
            claims = self._data.setdefault(claim_collection, {})
            documents = self._data.setdefault(collection, {})
            if claim_id in claims or doc_id in documents:
                return False
            claims[claim_id] = _clone(claim)
            documents[doc_id] = _clone(data)
            return True

    async def delete_if(self, collection: str, doc_id: str, where: Document) -> bool:
        """Delete only if the stored document still has the expected fields."""
        async with self._lock:
            documents = self._data.get(collection, {})
            found = documents.get(doc_id)
            if found is None or not _matches(found, where):
                return False
            del documents[doc_id]
            return True

    async def patch_if(
        self, collection: str, doc_id: str, changes: Document, where: Document
    ) -> bool:
        """Patch only if the stored document still has the expected fields."""
        async with self._lock:
            found = self._data.get(collection, {}).get(doc_id)
            if found is None or not _matches(found, where):
                return False
            found.update(_clone(changes))
            return True

    async def mutate(
        self, collection: str, doc_id: str, transform: Transform
    ) -> tuple[Document | None, bool]:
        """Atomically replace one document from its current value.

        A transform returning ``None`` declines the write and returns the
        current document with ``changed=False``.
        """
        async with self._lock:
            found = self._data.get(collection, {}).get(doc_id)
            if found is None:
                return None, False
            proposal = transform(_clone(found))
            if proposal is None:
                return _clone(found), False
            self._data[collection][doc_id] = _clone(proposal)
            return _clone(proposal), True


def _clone(document: Document) -> Document:
    from copy import deepcopy

    return deepcopy(document)


def _sort_key(value: Any) -> Any:
    """Order missing values consistently instead of raising on mixed types."""
    return (value is None, str(value) if value is not None else "")


class FileStore(InMemoryStore):
    """The in-memory store, persisted to one JSON file after every write.

    Local development only: a backend restart keeps users, shots and the
    connected folder. Not safe for concurrent processes, which is fine here.
    """

    def __init__(self, path: str | Path = "./.blobs/store.json"):
        super().__init__()
        self.path = Path(path)
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data), encoding="utf-8")
        tmp.replace(self.path)

    async def put(self, collection: str, doc_id: str, data: Document) -> None:
        await super().put(collection, doc_id, data)
        self._flush()

    async def delete(self, collection: str, doc_id: str) -> None:
        await super().delete(collection, doc_id)
        self._flush()

    async def create(self, collection: str, doc_id: str, data: Document) -> bool:
        created = await super().create(collection, doc_id, data)
        if created:
            self._flush()
        return created

    async def create_claimed(
        self,
        claim_collection: str,
        claim_id: str,
        claim: Document,
        collection: str,
        doc_id: str,
        data: Document,
    ) -> bool:
        created = await super().create_claimed(
            claim_collection, claim_id, claim, collection, doc_id, data
        )
        if created:
            self._flush()
        return created

    async def delete_if(self, collection: str, doc_id: str, where: Document) -> bool:
        deleted = await super().delete_if(collection, doc_id, where)
        if deleted:
            self._flush()
        return deleted

    async def patch_if(
        self, collection: str, doc_id: str, changes: Document, where: Document
    ) -> bool:
        changed = await super().patch_if(collection, doc_id, changes, where)
        if changed:
            self._flush()
        return changed

    async def mutate(
        self, collection: str, doc_id: str, transform: Transform
    ) -> tuple[Document | None, bool]:
        document, changed = await super().mutate(collection, doc_id, transform)
        if changed:
            self._flush()
        return document, changed


class FirestoreStore:
    """Production storage. Firestore's async client, no ORM (AGENTS.md)."""

    def __init__(self, client: Any = None, database: str | None = None):
        if client is None:
            from google.cloud import firestore

            from app.config import settings

            client = firestore.AsyncClient(
                project=settings.gcp_project or None,
                database=database or settings.firestore_database,
            )
        self._client = client

    async def put(self, collection: str, doc_id: str, data: Document) -> None:
        await self._client.collection(collection).document(doc_id).set(data)

    async def get(self, collection: str, doc_id: str) -> Document | None:
        snapshot = await self._client.collection(collection).document(doc_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    async def query(
        self,
        collection: str,
        where: Document | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
    ) -> list[Document]:
        from google.cloud.firestore import FieldFilter, Query

        query = self._client.collection(collection)
        for field, value in (where or {}).items():
            is_array_field = isinstance(value, str) and field.endswith("_ids")
            operator = "array_contains" if is_array_field else "=="
            query = query.where(filter=FieldFilter(field, operator, value))
        if order_by:
            direction = Query.DESCENDING if descending else Query.ASCENDING
            query = query.order_by(order_by, direction=direction)
        if limit is not None:
            query = query.limit(limit)

        return [snapshot.to_dict() async for snapshot in query.stream()]

    async def delete(self, collection: str, doc_id: str) -> None:
        await self._client.collection(collection).document(doc_id).delete()

    async def create(self, collection: str, doc_id: str, data: Document) -> bool:
        from google.api_core.exceptions import AlreadyExists

        try:
            await self._client.collection(collection).document(doc_id).create(data)
        except AlreadyExists:
            return False
        return True

    async def create_claimed(
        self,
        claim_collection: str,
        claim_id: str,
        claim: Document,
        collection: str,
        doc_id: str,
        data: Document,
    ) -> bool:
        from google.cloud import firestore

        claim_reference = self._client.collection(claim_collection).document(claim_id)
        document_reference = self._client.collection(collection).document(doc_id)
        transaction = self._client.transaction()

        @firestore.async_transactional
        async def create_both(transaction: Any) -> bool:
            claim_snapshot = await claim_reference.get(transaction=transaction)
            document_snapshot = await document_reference.get(transaction=transaction)
            if claim_snapshot.exists or document_snapshot.exists:
                return False
            transaction.create(claim_reference, claim)
            transaction.create(document_reference, data)
            return True

        return await create_both(transaction)

    async def delete_if(self, collection: str, doc_id: str, where: Document) -> bool:
        from google.cloud import firestore

        reference = self._client.collection(collection).document(doc_id)
        transaction = self._client.transaction()

        @firestore.async_transactional
        async def conditional_delete(transaction: Any) -> bool:
            snapshot = await reference.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else None
            if data is None or not _matches(data, where):
                return False
            transaction.delete(reference)
            return True

        return await conditional_delete(transaction)

    async def patch_if(
        self, collection: str, doc_id: str, changes: Document, where: Document
    ) -> bool:
        from google.cloud import firestore

        reference = self._client.collection(collection).document(doc_id)
        transaction = self._client.transaction()

        @firestore.async_transactional
        async def conditional_patch(transaction: Any) -> bool:
            snapshot = await reference.get(transaction=transaction)
            data = snapshot.to_dict() if snapshot.exists else None
            if data is None or not _matches(data, where):
                return False
            transaction.update(reference, changes)
            return True

        return await conditional_patch(transaction)

    async def mutate(
        self, collection: str, doc_id: str, transform: Transform
    ) -> tuple[Document | None, bool]:
        from google.cloud import firestore

        reference = self._client.collection(collection).document(doc_id)
        transaction = self._client.transaction()

        @firestore.async_transactional
        async def transactional_mutation(
            transaction: Any,
        ) -> tuple[Document | None, bool]:
            snapshot = await reference.get(transaction=transaction)
            if not snapshot.exists:
                return None, False
            current = snapshot.to_dict()
            proposal = transform(_clone(current))
            if proposal is None:
                return current, False
            transaction.set(reference, proposal)
            return proposal, True

        return await transactional_mutation(transaction)
