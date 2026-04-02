from typing import List
from pydantic import BaseModel


class EntitiesSchema(BaseModel):
    persons: List[str]
    organizations: List[str]
    dates: List[str]
    monetary_values: List[str]
    locations: List[str]


class AnalysisResponse(BaseModel):
    filename: str
    extracted_text_preview: str
    summary: str
    entities: EntitiesSchema
    sentiment: str

    model_config = {"json_schema_extra": {
        "example": {
            "filename": "contract.pdf",
            "extracted_text_preview": "This agreement is made between...",
            "summary": "A legal contract between two parties...",
            "entities": {
                "persons": ["John Doe"],
                "organizations": ["Acme Corp"],
                "dates": ["January 1, 2024"],
                "monetary_values": ["$50,000"],
                "locations": ["New York"],
            },
            "sentiment": "neutral",
        }
    }}