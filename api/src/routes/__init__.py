# Routes module
from src.routes.freshmart import router as freshmart_router
from src.routes.ontology import router as ontology_router
from src.routes.triples import router as triples_router

__all__ = ["freshmart_router", "ontology_router", "triples_router"]
