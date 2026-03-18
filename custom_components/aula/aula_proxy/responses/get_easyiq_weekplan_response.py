from typing import List, TypedDict


class AulaEasyiqWeekplanEvent(TypedDict):
    start: str
    end: str
    itemType: str
    title: str
    ownername: str
    description: str


class AulaGetEasyiqWeekplanResponse(TypedDict):
    Events: List[AulaEasyiqWeekplanEvent]
