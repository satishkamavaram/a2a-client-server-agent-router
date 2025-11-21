from pydantic import BaseModel


class ResponseStatus(BaseModel):
    status: str
    txid: str
    message: str
