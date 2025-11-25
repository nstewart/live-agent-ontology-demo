"""Ontology domain models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class OntologyClassBase(BaseModel):
    """Base model for ontology class."""

    class_name: str = Field(..., description="Human-readable class name", examples=["Customer", "Order"])
    prefix: str = Field(..., description="Subject ID prefix", examples=["customer", "order"])
    description: Optional[str] = Field(None, description="Class description")
    parent_class_id: Optional[int] = Field(None, description="Parent class ID for hierarchy")


class OntologyClassCreate(OntologyClassBase):
    """Model for creating an ontology class."""

    pass


class OntologyClassUpdate(BaseModel):
    """Model for updating an ontology class."""

    class_name: Optional[str] = None
    description: Optional[str] = None
    parent_class_id: Optional[int] = None


class OntologyClass(OntologyClassBase):
    """Full ontology class model."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OntologyPropertyBase(BaseModel):
    """Base model for ontology property."""

    prop_name: str = Field(..., description="Property name", examples=["customer_name", "order_status"])
    domain_class_id: int = Field(..., description="Domain class ID (subject type)")
    range_kind: str = Field(
        ...,
        description="Range type",
        examples=["string", "int", "float", "timestamp", "date", "bool", "entity_ref"],
    )
    range_class_id: Optional[int] = Field(None, description="Range class ID (for entity_ref)")
    is_multi_valued: bool = Field(True, description="Whether property can have multiple values")
    is_required: bool = Field(False, description="Whether property is required")
    description: Optional[str] = Field(None, description="Property description")


class OntologyPropertyCreate(OntologyPropertyBase):
    """Model for creating an ontology property."""

    pass


class OntologyPropertyUpdate(BaseModel):
    """Model for updating an ontology property."""

    description: Optional[str] = None
    is_multi_valued: Optional[bool] = None
    is_required: Optional[bool] = None


class OntologyProperty(OntologyPropertyBase):
    """Full ontology property model."""

    id: int
    created_at: datetime
    updated_at: datetime

    # Joined fields
    domain_class_name: Optional[str] = None
    range_class_name: Optional[str] = None

    class Config:
        from_attributes = True


class OntologySchema(BaseModel):
    """Complete ontology schema."""

    classes: list[OntologyClass]
    properties: list[OntologyProperty]
