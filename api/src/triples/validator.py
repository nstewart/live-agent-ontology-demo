"""Triple validation against ontology schema."""

from typing import Optional

from src.ontology.service import OntologyService
from src.triples.models import ObjectType, TripleCreate, ValidationErrorDetail, ValidationResult


class TripleValidator:
    """
    Validates triples against the ontology schema.

    Validation rules:
    1. Subject prefix must correspond to a valid ontology class
    2. Predicate must exist in ontology_properties
    3. Predicate's domain must match subject's class
    4. Object type must match predicate's range_kind
    5. For entity_ref, object prefix must match predicate's range_class
    """

    def __init__(self, ontology_service: OntologyService):
        self.ontology = ontology_service

    async def validate(self, triple: TripleCreate) -> ValidationResult:
        """Validate a triple against the ontology schema."""
        errors = []

        # Extract prefix from subject_id
        subject_prefix = triple.subject_id.split(":")[0]

        # 1. Check subject class exists
        subject_class = await self.ontology.get_class_by_prefix(subject_prefix)
        if not subject_class:
            errors.append(
                ValidationErrorDetail(
                    error_type="unknown_class",
                    message=f"No ontology class found for prefix '{subject_prefix}'",
                    actual=subject_prefix,
                )
            )
            return ValidationResult(is_valid=False, errors=errors)

        # 2. Check predicate exists
        prop = await self.ontology.get_property_by_name(triple.predicate)
        if not prop:
            errors.append(
                ValidationErrorDetail(
                    error_type="unknown_predicate",
                    message=f"Predicate '{triple.predicate}' not found in ontology",
                    predicate=triple.predicate,
                )
            )
            return ValidationResult(is_valid=False, errors=errors)

        # 3. Check domain constraint
        if prop.domain_class_id != subject_class.id:
            # Check if subject class is a subclass of domain class
            if not await self._is_subclass_of(subject_class.id, prop.domain_class_id):
                errors.append(
                    ValidationErrorDetail(
                        error_type="domain_violation",
                        message=f"Predicate '{triple.predicate}' domain is '{prop.domain_class_name}', "
                        f"but subject is '{subject_class.class_name}'",
                        predicate=triple.predicate,
                        expected=prop.domain_class_name,
                        actual=subject_class.class_name,
                    )
                )

        # 4. Check range type
        range_kind_to_object_type = {
            "string": ObjectType.STRING,
            "int": ObjectType.INT,
            "float": ObjectType.FLOAT,
            "timestamp": ObjectType.TIMESTAMP,
            "date": ObjectType.DATE,
            "bool": ObjectType.BOOL,
            "entity_ref": ObjectType.ENTITY_REF,
        }

        expected_object_type = range_kind_to_object_type.get(prop.range_kind)
        if expected_object_type and triple.object_type != expected_object_type:
            errors.append(
                ValidationErrorDetail(
                    error_type="range_type_mismatch",
                    message=f"Predicate '{triple.predicate}' expects type '{prop.range_kind}', "
                    f"got '{triple.object_type.value}'",
                    predicate=triple.predicate,
                    expected=prop.range_kind,
                    actual=triple.object_type.value,
                )
            )

        # 5. For entity_ref, validate object prefix matches range class
        if triple.object_type == ObjectType.ENTITY_REF:
            if ":" not in triple.object_value:
                errors.append(
                    ValidationErrorDetail(
                        error_type="invalid_entity_ref",
                        message="Entity reference must be in format 'prefix:id'",
                        actual=triple.object_value,
                    )
                )
            else:
                object_prefix = triple.object_value.split(":")[0]
                if prop.range_class_id:
                    range_class = await self.ontology.get_class(prop.range_class_id)
                    if range_class and object_prefix != range_class.prefix:
                        # Check if object class is subclass of range class
                        object_class = await self.ontology.get_class_by_prefix(object_prefix)
                        if object_class and not await self._is_subclass_of(object_class.id, prop.range_class_id):
                            errors.append(
                                ValidationErrorDetail(
                                    error_type="range_class_mismatch",
                                    message=f"Entity reference should be of type '{range_class.class_name}' "
                                    f"(prefix '{range_class.prefix}'), got prefix '{object_prefix}'",
                                    predicate=triple.predicate,
                                    expected=range_class.prefix,
                                    actual=object_prefix,
                                )
                            )

        # 6. Validate literal values
        if triple.object_type in [ObjectType.INT, ObjectType.FLOAT, ObjectType.BOOL]:
            validation_error = self._validate_literal(triple.object_value, triple.object_type)
            if validation_error:
                errors.append(validation_error)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def _is_subclass_of(self, class_id: int, parent_class_id: int) -> bool:
        """Check if class is a subclass of parent (including transitive)."""
        if class_id == parent_class_id:
            return True

        current_class = await self.ontology.get_class(class_id)
        while current_class and current_class.parent_class_id:
            if current_class.parent_class_id == parent_class_id:
                return True
            current_class = await self.ontology.get_class(current_class.parent_class_id)

        return False

    def _validate_literal(self, value: str, object_type: ObjectType) -> Optional[ValidationErrorDetail]:
        """Validate literal value matches expected type."""
        if object_type == ObjectType.INT:
            try:
                int(value)
            except ValueError:
                return ValidationErrorDetail(
                    error_type="invalid_literal",
                    message=f"Value '{value}' is not a valid integer",
                    expected="integer",
                    actual=value,
                )

        elif object_type == ObjectType.FLOAT:
            try:
                float(value)
            except ValueError:
                return ValidationErrorDetail(
                    error_type="invalid_literal",
                    message=f"Value '{value}' is not a valid float",
                    expected="float",
                    actual=value,
                )

        elif object_type == ObjectType.BOOL:
            if value.lower() not in ("true", "false"):
                return ValidationErrorDetail(
                    error_type="invalid_literal",
                    message=f"Value '{value}' is not a valid boolean (expected 'true' or 'false')",
                    expected="true or false",
                    actual=value,
                )

        return None
