from typing import Any, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class CountryIntent(BaseModel):
    country: str = Field(
        description= "Name of the country in English, properly capiatlised"
    )
    fields: list[str] = Field(
        description= "Fields requested. Allowed: population, capital, currencies, languages, area, region, subregion, flag"
    )

    original_query: str = Field(
        description= "The user's original question, unchanged."
    )

class AgentState(TypedDict, total = False):
    query : str

    intent : Optional[dict[str, Any]]

    raw_data: Optional[dict[str, Any]]

    answer : Optional[str]

    error: Optional[str]