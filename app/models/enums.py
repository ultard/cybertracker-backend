from enum import StrEnum


class UserRole(StrEnum):
    admin = "admin"
    organizer = "organizer"
    manager = "manager"
    judge = "judge"
    user = "user"


class TournamentStatus(StrEnum):
    draft = "draft"
    recruiting = "recruiting"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    archived = "archived"


class TournamentType(StrEnum):
    online = "online"
    offline = "offline"


class ParticipantRole(StrEnum):
    player = "player"
    spectator = "spectator"


class ParticipantStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    disqualified = "disqualified"
    banned = "banned"
    cancelled = "cancelled"
