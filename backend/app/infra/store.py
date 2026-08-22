"""Document storage behind a four-method interface.

Two real implementations, not a mock and a real one:

* ``InMemoryStore`` — a genuine store with real query and ordering semantics. Runs
  the test suite and local development.
* ``FirestoreStore`` — production.

Both are exercised by the same contract tests (``tests/test_store_contract.py``), so
a behavioural difference between them is a test failure rather than a surprise in
production. This is what AGENTS.md means by no mocked repositories: nothing here
pretends to store something and then asserts it was asked to.
"""

from typing import Any, Protocol, runtime_checkable

Document = dict[str, Any]


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

    async def put(self, collection: str, doc_id: str, data: Document) -> None:
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
        self._data.get(collection, {}).pop(doc_id, None)


def _clone(document: Document) -> Document:
    from copy import deepcopy

    return deepcopy(document)


def _sort_key(value: Any) -> Any:
    """Order missing values consistently instead of raising on mixed types."""
    return (value is None, str(value) if value is not None else "")


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
