from enum import StrEnum


class UserRoleName(StrEnum):
    admin = "admin"
    organizer = "organizer"
    judge = "judge"
    manager = "manager"
    player = "player"
    spectator = "spectator"


class TournamentStatus(StrEnum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class TournamentType(StrEnum):
    online = "online"
    offline = "offline"


class RegistrationStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"


class ParticipantStatus(StrEnum):
    active = "active"
    blocked = "blocked"
