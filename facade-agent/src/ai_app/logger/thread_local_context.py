import contextvars
import uuid

txid = contextvars.ContextVar("txid", default=None)
ws = contextvars.ContextVar("ws", default=None)


def get_txid() -> str:
    return txid.get()


def set_txid() -> None:
    txid.set(str(uuid.uuid4()))


def set_transaction_id(transaction_id: str) -> None:
    txid.set(transaction_id)


def clear_txid() -> None:
    txid.set(None)


def set_websocket(websocket) -> None:
    ws.set(websocket)


def get_websocket():
    return ws.get()


def clear_websocket() -> None:
    ws.set(None)
