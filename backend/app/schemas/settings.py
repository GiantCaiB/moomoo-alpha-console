from pydantic import BaseModel, model_validator


class TradingUniverseRequest(BaseModel):
    symbols: list[str]

    @model_validator(mode="after")
    def normalize_and_validate(self) -> "TradingUniverseRequest":
        normalized = [s.upper().strip() for s in self.symbols if s.strip()]
        seen: set[str] = set()
        deduped: list[str] = []
        for s in normalized:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        self.symbols = deduped
        if not self.symbols:
            raise ValueError("Trading universe cannot be empty")
        return self


class TradingUniverseResponse(BaseModel):
    symbols: list[str]
    source: str
