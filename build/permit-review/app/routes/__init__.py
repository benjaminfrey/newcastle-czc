"""HTTP route modules. Each exposes an `APIRouter` named `router`;
app/main.py includes it into the app factory. Business logic lives in the
sibling top-level module (e.g. app/routes/cases.py <-> app/cases.py) so it
stays importable and testable without FastAPI in the loop.
"""
