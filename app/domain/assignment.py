from app.domain.enums import ServiceType, TeamType
from app.domain.state import ConversationState


TEAM_NAMES = {
    TeamType.REAL_ESTATE: "Real Estate Team",
    TeamType.INSURANCE: "Insurance Team",
    TeamType.IT: "IT/Technology Team",
    TeamType.GENERAL: "Business/Customer Support",
}


def assign_team(
    state: ConversationState,
) -> TeamType:
    """
    Determine the internal team responsible for the lead.
    """

    if state.service == ServiceType.REAL_ESTATE:
        return TeamType.REAL_ESTATE

    if state.service == ServiceType.INSURANCE:
        return TeamType.INSURANCE

    if state.service == ServiceType.IT_SERVICES:
        return TeamType.IT

    return TeamType.GENERAL


def get_team_name(
    team: TeamType,
) -> str:
    """
    Return the human-readable team name.
    """

    return TEAM_NAMES.get(
        team,
        "Business/Customer Support",
    )