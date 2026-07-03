from pydantic import BaseModel


class WatchlistItemResponse(BaseModel):
    id: str
    symbol: str
    list_name: str
    sort_order: int
    notes: str | None
    added_price: float | None


class WatchlistAddRequest(BaseModel):
    symbol: str
    list_name: str = "default"
    notes: str | None = None
