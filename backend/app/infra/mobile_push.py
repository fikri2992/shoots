"""Native Android notifications through Firebase Cloud Messaging."""

import asyncio
import threading
from typing import Protocol, runtime_checkable


@runtime_checkable
class MobilePush(Protocol):
    async def send(self, target: str, payload: dict[str, str], *, tag: str) -> bool: ...


class FirebaseMobilePush:
    """ADC-backed Firebase adapter. No service-account key file is required."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self._app = None
        self._lock = threading.Lock()

    def _firebase_app(self):
        if self._app is not None:
            return self._app
        with self._lock:
            if self._app is not None:
                return self._app
            import firebase_admin
            from firebase_admin import credentials

            name = f"shoots-{self.project_id}"
            try:
                self._app = firebase_admin.get_app(name)
            except ValueError:
                self._app = firebase_admin.initialize_app(
                    credentials.ApplicationDefault(),
                    {"projectId": self.project_id},
                    name=name,
                )
            return self._app

    async def send(self, target: str, payload: dict[str, str], *, tag: str) -> bool:
        def deliver() -> bool:
            from firebase_admin import messaging

            try:
                messaging.send(
                    messaging.Message(
                        data={key: str(value) for key, value in payload.items()},
                        fid=target,
                        android=messaging.AndroidConfig(collapse_key=tag, priority="normal"),
                    ),
                    app=self._firebase_app(),
                )
                return True
            except messaging.UnregisteredError:
                return False

        return await asyncio.to_thread(deliver)
