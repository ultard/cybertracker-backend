from fastapi import APIRouter

from app.openapi import (
    TAG_AUDIT,
    TAG_AUTH,
    TAG_DISCIPLINES,
    TAG_MATCHES,
    TAG_PARTICIPANTS,
    TAG_PREDICT,
    TAG_QR,
    TAG_TOURNAMENTS,
    TAG_USERS,
)
from app.routers import (
    auth,
    discipline,
    identity,
    system,
    tournament,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=[TAG_AUTH])
api_router.include_router(identity.users_router, prefix="/users", tags=[TAG_USERS])
api_router.include_router(discipline.router, prefix="/disciplines", tags=[TAG_DISCIPLINES])
api_router.include_router(
    tournament.tournaments_router, prefix="/tournaments", tags=[TAG_TOURNAMENTS]
)
api_router.include_router(
    tournament.participants_router, prefix="/participants", tags=[TAG_PARTICIPANTS]
)
api_router.include_router(tournament.matches_router, prefix="/matches", tags=[TAG_MATCHES])
api_router.include_router(system.qr_router, prefix="/qr", tags=[TAG_QR])
api_router.include_router(system.audit_router, prefix="/audit", tags=[TAG_AUDIT])
api_router.include_router(system.predict_router, prefix="/predict", tags=[TAG_PREDICT])
