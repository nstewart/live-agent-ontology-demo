"""Ontology API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.client import get_pg_session_factory
from src.ontology.models import (
    OntologyClass,
    OntologyClassCreate,
    OntologyClassUpdate,
    OntologyProperty,
    OntologyPropertyCreate,
    OntologyPropertyUpdate,
    OntologySchema,
)
from src.ontology.service import OntologyService

router = APIRouter(prefix="/ontology", tags=["Ontology"])


async def get_session() -> AsyncSession:
    """Dependency to get database session."""
    factory = get_pg_session_factory()
    async with factory() as session:
        yield session


async def get_ontology_service(session: AsyncSession = Depends(get_session)) -> OntologyService:
    """Dependency to get ontology service."""
    return OntologyService(session)


# =============================================================================
# Classes
# =============================================================================


@router.get("/classes", response_model=list[OntologyClass])
async def list_classes(service: OntologyService = Depends(get_ontology_service)):
    """List all ontology classes."""
    return await service.list_classes()


@router.get("/classes/{class_id}", response_model=OntologyClass)
async def get_class(class_id: int, service: OntologyService = Depends(get_ontology_service)):
    """Get an ontology class by ID."""
    ont_class = await service.get_class(class_id)
    if not ont_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return ont_class


@router.post("/classes", response_model=OntologyClass, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: OntologyClassCreate,
    service: OntologyService = Depends(get_ontology_service),
):
    """Create a new ontology class."""
    # Check for duplicates
    existing = await service.get_class_by_name(data.class_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Class '{data.class_name}' already exists",
        )

    existing = await service.get_class_by_prefix(data.prefix)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Prefix '{data.prefix}' already in use by class '{existing.class_name}'",
        )

    return await service.create_class(data)


@router.patch("/classes/{class_id}", response_model=OntologyClass)
async def update_class(
    class_id: int,
    data: OntologyClassUpdate,
    service: OntologyService = Depends(get_ontology_service),
):
    """Update an ontology class."""
    updated = await service.update_class(class_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return updated


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(class_id: int, service: OntologyService = Depends(get_ontology_service)):
    """Delete an ontology class."""
    deleted = await service.delete_class(class_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")


# =============================================================================
# Properties
# =============================================================================


@router.get("/properties", response_model=list[OntologyProperty])
async def list_properties(
    domain_class_id: Optional[int] = None,
    service: OntologyService = Depends(get_ontology_service),
):
    """List all ontology properties, optionally filtered by domain class."""
    return await service.list_properties(domain_class_id=domain_class_id)


@router.get("/class/{class_name}/properties", response_model=list[OntologyProperty])
async def get_class_properties(
    class_name: str,
    service: OntologyService = Depends(get_ontology_service),
):
    """Get all properties for a class by name."""
    ont_class = await service.get_class_by_name(class_name)
    if not ont_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return await service.list_properties(domain_class_id=ont_class.id)


@router.get("/properties/{prop_id}", response_model=OntologyProperty)
async def get_property(prop_id: int, service: OntologyService = Depends(get_ontology_service)):
    """Get an ontology property by ID."""
    prop = await service.get_property(prop_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return prop


@router.post("/properties", response_model=OntologyProperty, status_code=status.HTTP_201_CREATED)
async def create_property(
    data: OntologyPropertyCreate,
    service: OntologyService = Depends(get_ontology_service),
):
    """Create a new ontology property."""
    # Check for duplicate
    existing = await service.get_property_by_name(data.prop_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Property '{data.prop_name}' already exists",
        )

    # Validate domain class exists
    domain_class = await service.get_class(data.domain_class_id)
    if not domain_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain class ID {data.domain_class_id} not found",
        )

    # Validate range class exists if specified
    if data.range_class_id:
        range_class = await service.get_class(data.range_class_id)
        if not range_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Range class ID {data.range_class_id} not found",
            )

    return await service.create_property(data)


@router.patch("/properties/{prop_id}", response_model=OntologyProperty)
async def update_property(
    prop_id: int,
    data: OntologyPropertyUpdate,
    service: OntologyService = Depends(get_ontology_service),
):
    """Update an ontology property."""
    updated = await service.update_property(prop_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return updated


@router.delete("/properties/{prop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(prop_id: int, service: OntologyService = Depends(get_ontology_service)):
    """Delete an ontology property."""
    deleted = await service.delete_property(prop_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")


# =============================================================================
# Schema
# =============================================================================


@router.get("/schema", response_model=OntologySchema)
async def get_schema(service: OntologyService = Depends(get_ontology_service)):
    """Get the complete ontology schema (classes and properties)."""
    return await service.get_full_schema()
