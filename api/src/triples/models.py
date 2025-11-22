"""Triple domain models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ObjectType(str, Enum):
    """Supported object types for triples."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    TIMESTAMP = "timestamp"
    DATE = "date"
    BOOL = "bool"
    ENTITY_REF = "entity_ref"


class TripleBase(BaseModel):
    """Base model for triple."""

    subject_id: str = Field(
        ...,
        description="Subject identifier in format 'prefix:id'",
        examples=["customer:123", "order:FM-1001"],
    )
    predicate: str = Field(
        ...,
        description="Property name from ontology",
        examples=["customer_name", "order_status"],
    )
    object_value: str = Field(..., description="The value (literal or entity reference)")
    object_type: ObjectType = Field(..., description="Type of the object value")

    @field_validator("subject_id")
    @classmethod
    def validate_subject_id(cls, v: str) -> str:
        """Validate subject_id format."""
        if ":" not in v:
            raise ValueError("subject_id must be in format 'prefix:id'")
        return v


class TripleCreate(TripleBase):
    """Model for creating a triple."""

    pass


class TripleUpdate(BaseModel):
    """Model for updating a triple (only object_value can change)."""

    object_value: str = Field(..., description="New value for the triple")


class Triple(TripleBase):
    """Full triple model."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TripleFilter(BaseModel):
    """Filter options for querying triples."""

    subject_id: Optional[str] = None
    predicate: Optional[str] = None
    object_value: Optional[str] = None
    object_type: Optional[ObjectType] = None


class SubjectInfo(BaseModel):
    """Information about a subject."""

    subject_id: str
    class_name: Optional[str] = None
    class_id: Optional[int] = None
    triples: list[Triple] = []


class ValidationErrorDetail(BaseModel):
    """Details of a validation error."""

    error_type: str
    message: str
    predicate: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of triple validation."""

    is_valid: bool
    errors: list[ValidationErrorDetail] = []
