"""Ontology service for CRUD operations."""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.ontology.models import (
    OntologyClass,
    OntologyClassCreate,
    OntologyClassUpdate,
    OntologyProperty,
    OntologyPropertyCreate,
    OntologyPropertyUpdate,
    OntologySchema,
)


class OntologyService:
    """Service for ontology management."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # Classes
    # =========================================================================

    async def list_classes(self) -> list[OntologyClass]:
        """List all ontology classes."""
        result = await self.session.execute(
            text("""
                SELECT id, class_name, prefix, description, parent_class_id,
                       created_at, updated_at
                FROM ontology_classes
                ORDER BY class_name
            """)
        )
        rows = result.fetchall()
        return [
            OntologyClass(
                id=row.id,
                class_name=row.class_name,
                prefix=row.prefix,
                description=row.description,
                parent_class_id=row.parent_class_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def get_class(self, class_id: int) -> Optional[OntologyClass]:
        """Get an ontology class by ID."""
        result = await self.session.execute(
            text("""
                SELECT id, class_name, prefix, description, parent_class_id,
                       created_at, updated_at
                FROM ontology_classes
                WHERE id = :class_id
            """),
            {"class_id": class_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return OntologyClass(
            id=row.id,
            class_name=row.class_name,
            prefix=row.prefix,
            description=row.description,
            parent_class_id=row.parent_class_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_class_by_name(self, class_name: str) -> Optional[OntologyClass]:
        """Get an ontology class by name."""
        result = await self.session.execute(
            text("""
                SELECT id, class_name, prefix, description, parent_class_id,
                       created_at, updated_at
                FROM ontology_classes
                WHERE class_name = :class_name
            """),
            {"class_name": class_name},
        )
        row = result.fetchone()
        if not row:
            return None
        return OntologyClass(
            id=row.id,
            class_name=row.class_name,
            prefix=row.prefix,
            description=row.description,
            parent_class_id=row.parent_class_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_class_by_prefix(self, prefix: str) -> Optional[OntologyClass]:
        """Get an ontology class by prefix."""
        result = await self.session.execute(
            text("""
                SELECT id, class_name, prefix, description, parent_class_id,
                       created_at, updated_at
                FROM ontology_classes
                WHERE prefix = :prefix
            """),
            {"prefix": prefix},
        )
        row = result.fetchone()
        if not row:
            return None
        return OntologyClass(
            id=row.id,
            class_name=row.class_name,
            prefix=row.prefix,
            description=row.description,
            parent_class_id=row.parent_class_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create_class(self, data: OntologyClassCreate) -> OntologyClass:
        """Create a new ontology class."""
        result = await self.session.execute(
            text("""
                INSERT INTO ontology_classes (class_name, prefix, description, parent_class_id)
                VALUES (:class_name, :prefix, :description, :parent_class_id)
                RETURNING id, class_name, prefix, description, parent_class_id,
                          created_at, updated_at
            """),
            {
                "class_name": data.class_name,
                "prefix": data.prefix,
                "description": data.description,
                "parent_class_id": data.parent_class_id,
            },
        )
        row = result.fetchone()
        return OntologyClass(
            id=row.id,
            class_name=row.class_name,
            prefix=row.prefix,
            description=row.description,
            parent_class_id=row.parent_class_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def update_class(self, class_id: int, data: OntologyClassUpdate) -> Optional[OntologyClass]:
        """Update an ontology class."""
        # Build dynamic update
        updates = []
        params = {"class_id": class_id}

        if data.class_name is not None:
            updates.append("class_name = :class_name")
            params["class_name"] = data.class_name
        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.parent_class_id is not None:
            updates.append("parent_class_id = :parent_class_id")
            params["parent_class_id"] = data.parent_class_id

        if not updates:
            return await self.get_class(class_id)

        query = f"""
            UPDATE ontology_classes
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = :class_id
            RETURNING id, class_name, prefix, description, parent_class_id,
                      created_at, updated_at
        """
        result = await self.session.execute(text(query), params)
        row = result.fetchone()
        if not row:
            return None
        return OntologyClass(
            id=row.id,
            class_name=row.class_name,
            prefix=row.prefix,
            description=row.description,
            parent_class_id=row.parent_class_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def delete_class(self, class_id: int) -> bool:
        """Delete an ontology class."""
        result = await self.session.execute(
            text("DELETE FROM ontology_classes WHERE id = :class_id"),
            {"class_id": class_id},
        )
        return result.rowcount > 0

    # =========================================================================
    # Properties
    # =========================================================================

    async def list_properties(self, domain_class_id: Optional[int] = None) -> list[OntologyProperty]:
        """List ontology properties, optionally filtered by domain class."""
        query = """
            SELECT p.id, p.prop_name, p.domain_class_id, p.range_kind, p.range_class_id,
                   p.is_multi_valued, p.is_required, p.description, p.created_at, p.updated_at,
                   dc.class_name AS domain_class_name,
                   rc.class_name AS range_class_name
            FROM ontology_properties p
            JOIN ontology_classes dc ON dc.id = p.domain_class_id
            LEFT JOIN ontology_classes rc ON rc.id = p.range_class_id
        """
        params = {}

        if domain_class_id is not None:
            query += " WHERE p.domain_class_id = :domain_class_id"
            params["domain_class_id"] = domain_class_id

        query += " ORDER BY p.prop_name"

        result = await self.session.execute(text(query), params)
        rows = result.fetchall()
        return [
            OntologyProperty(
                id=row.id,
                prop_name=row.prop_name,
                domain_class_id=row.domain_class_id,
                range_kind=row.range_kind,
                range_class_id=row.range_class_id,
                is_multi_valued=row.is_multi_valued,
                is_required=row.is_required,
                description=row.description,
                created_at=row.created_at,
                updated_at=row.updated_at,
                domain_class_name=row.domain_class_name,
                range_class_name=row.range_class_name,
            )
            for row in rows
        ]

    async def get_property(self, prop_id: int) -> Optional[OntologyProperty]:
        """Get an ontology property by ID."""
        result = await self.session.execute(
            text("""
                SELECT p.id, p.prop_name, p.domain_class_id, p.range_kind, p.range_class_id,
                       p.is_multi_valued, p.is_required, p.description, p.created_at, p.updated_at,
                       dc.class_name AS domain_class_name,
                       rc.class_name AS range_class_name
                FROM ontology_properties p
                JOIN ontology_classes dc ON dc.id = p.domain_class_id
                LEFT JOIN ontology_classes rc ON rc.id = p.range_class_id
                WHERE p.id = :prop_id
            """),
            {"prop_id": prop_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return OntologyProperty(
            id=row.id,
            prop_name=row.prop_name,
            domain_class_id=row.domain_class_id,
            range_kind=row.range_kind,
            range_class_id=row.range_class_id,
            is_multi_valued=row.is_multi_valued,
            is_required=row.is_required,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
            domain_class_name=row.domain_class_name,
            range_class_name=row.range_class_name,
        )

    async def get_property_by_name(self, prop_name: str) -> Optional[OntologyProperty]:
        """Get an ontology property by name."""
        result = await self.session.execute(
            text("""
                SELECT p.id, p.prop_name, p.domain_class_id, p.range_kind, p.range_class_id,
                       p.is_multi_valued, p.is_required, p.description, p.created_at, p.updated_at,
                       dc.class_name AS domain_class_name,
                       rc.class_name AS range_class_name
                FROM ontology_properties p
                JOIN ontology_classes dc ON dc.id = p.domain_class_id
                LEFT JOIN ontology_classes rc ON rc.id = p.range_class_id
                WHERE p.prop_name = :prop_name
            """),
            {"prop_name": prop_name},
        )
        row = result.fetchone()
        if not row:
            return None
        return OntologyProperty(
            id=row.id,
            prop_name=row.prop_name,
            domain_class_id=row.domain_class_id,
            range_kind=row.range_kind,
            range_class_id=row.range_class_id,
            is_multi_valued=row.is_multi_valued,
            is_required=row.is_required,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
            domain_class_name=row.domain_class_name,
            range_class_name=row.range_class_name,
        )

    async def create_property(self, data: OntologyPropertyCreate) -> OntologyProperty:
        """Create a new ontology property."""
        result = await self.session.execute(
            text("""
                INSERT INTO ontology_properties
                    (prop_name, domain_class_id, range_kind, range_class_id,
                     is_multi_valued, is_required, description)
                VALUES (:prop_name, :domain_class_id, :range_kind, :range_class_id,
                        :is_multi_valued, :is_required, :description)
                RETURNING id, prop_name, domain_class_id, range_kind, range_class_id,
                          is_multi_valued, is_required, description, created_at, updated_at
            """),
            {
                "prop_name": data.prop_name,
                "domain_class_id": data.domain_class_id,
                "range_kind": data.range_kind,
                "range_class_id": data.range_class_id,
                "is_multi_valued": data.is_multi_valued,
                "is_required": data.is_required,
                "description": data.description,
            },
        )
        row = result.fetchone()

        # Fetch with joined class names
        return await self.get_property(row.id)

    async def update_property(self, prop_id: int, data: OntologyPropertyUpdate) -> Optional[OntologyProperty]:
        """Update an ontology property."""
        updates = []
        params = {"prop_id": prop_id}

        if data.description is not None:
            updates.append("description = :description")
            params["description"] = data.description
        if data.is_multi_valued is not None:
            updates.append("is_multi_valued = :is_multi_valued")
            params["is_multi_valued"] = data.is_multi_valued
        if data.is_required is not None:
            updates.append("is_required = :is_required")
            params["is_required"] = data.is_required

        if not updates:
            return await self.get_property(prop_id)

        query = f"""
            UPDATE ontology_properties
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = :prop_id
            RETURNING id
        """
        result = await self.session.execute(text(query), params)
        row = result.fetchone()
        if not row:
            return None
        return await self.get_property(prop_id)

    async def delete_property(self, prop_id: int) -> bool:
        """Delete an ontology property."""
        result = await self.session.execute(
            text("DELETE FROM ontology_properties WHERE id = :prop_id"),
            {"prop_id": prop_id},
        )
        return result.rowcount > 0

    # =========================================================================
    # Schema
    # =========================================================================

    async def get_full_schema(self) -> OntologySchema:
        """Get the complete ontology schema."""
        classes = await self.list_classes()
        properties = await self.list_properties()
        return OntologySchema(classes=classes, properties=properties)
