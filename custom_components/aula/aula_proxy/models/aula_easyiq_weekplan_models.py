from dataclasses import dataclass
import datetime
from typing import List, Optional


@dataclass
class AulaEasyiqEvent:
    """An event from the EasyIQ weekly plan API.

    id: Generated unique ID (hash of child + start + end + title)
    title: Event title (from title field if itemType=="5", else from ownername)
    description: Event description/content
    owner_name: Teacher/owner name
    item_type: EasyIQ item type string (e.g. "5")
    start_time: Event start time
    end_time: Event end time
    """
    id: int
    title: str
    description: str
    owner_name: str
    item_type: str
    start_time: datetime.time
    end_time: datetime.time


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
