from dataclasses import dataclass
import datetime
from typing import List


@dataclass
class AulaEasyiqEvent:
    """An event from the EasyIQ weekly plan API.

    id: Generated stable unique ID (sha256 of child + start + end + title)
    title: Event title (from title field if itemType=="5", else from ownername)
    description: Event description/content
    owner_name: Teacher/owner name
    item_type: EasyIQ item type string (e.g. "5")
    start: Event start datetime
    end: Event end datetime
    """
    id: str
    title: str
    description: str
    owner_name: str
    item_type: str
    start: datetime.datetime
    end: datetime.datetime


@dataclass
class AulaEasyiqDailyPlan:
    date: datetime.date
    events: List[AulaEasyiqEvent]


@dataclass
class AulaEasyiqWeeklyPlan:
    name: str
    from_date: datetime.date
    to_date: datetime.date
    daily_plans: List[AulaEasyiqDailyPlan]
