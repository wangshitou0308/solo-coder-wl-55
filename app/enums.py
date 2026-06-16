import enum


class BeardCategory(str, enum.Enum):
    NATURAL_GOATEE = "natural_goatee"
    NATURAL_MOUSTACHE = "natural_moustache"
    CARIBBEAN_PIRATE = "caribbean_pirate"
    IMPERIAL = "imperial"
    DALI = "dali"
    FREESTYLE = "freestyle"
    FULL_BEARD = "full_beard"


class RegistrationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AwardType(str, enum.Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    BEST_NEWCOMER = "best_newcomer"
    OVERALL_CHAMPION = "overall_champion"


class PhotoType(str, enum.Enum):
    PROFILE = "profile"
    BEARD_CLOSEUP = "beard_closeup"


SCORING_DIMENSIONS = {
    "creativity": 0.25,
    "symmetry": 0.20,
    "maintenance": 0.20,
    "stage_presence": 0.15,
    "overall_impression": 0.20,
}

AWARD_POINTS = {
    AwardType.GOLD: 10,
    AwardType.SILVER: 7,
    AwardType.BRONZE: 5,
    AwardType.BEST_NEWCOMER: 8,
    AwardType.OVERALL_CHAMPION: 15,
}
