# Ontology module
from src.ontology.models import (
    OntologyClass,
    OntologyClassCreate,
    OntologyProperty,
    OntologyPropertyCreate,
    OntologySchema,
)
from src.ontology.service import OntologyService

__all__ = [
    "OntologyClass",
    "OntologyClassCreate",
    "OntologyProperty",
    "OntologyPropertyCreate",
    "OntologySchema",
    "OntologyService",
]
