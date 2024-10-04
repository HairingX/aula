from dataclasses import dataclass
import datetime
from typing import List, Optional

@dataclass
class AulaDailyPlanTask:
    author: str
    content: str
    group: str
    id: int
    pill: str
    type: str
    editUrl: Optional[str|None] = None

@dataclass
class AulaDailyPlan:
    date: datetime.date
    tasks: List[AulaDailyPlanTask]

@dataclass
class AulaWeeklyPlan:
    from_date: datetime.date
    name: str
    to_date: datetime.date
    unilogin: str
    daily_plans: List[AulaDailyPlan]