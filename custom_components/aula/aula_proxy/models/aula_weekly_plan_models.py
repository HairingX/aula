import datetime
from typing import List, NotRequired, TypedDict


class AulaDailyPlanTask(TypedDict):
    id: int
    type: str
    author: str
    group: str
    pill: str
    content: str
    editUrl: NotRequired[str|None]

class AulaDailyPlan(TypedDict):
    date: datetime.date
    tasks: List[AulaDailyPlanTask]

class AulaWeeklyPlan(TypedDict):
    from_date: datetime.date
    to_date: datetime.date
    name: str
    unilogin: str
    daily_plans: List[AulaDailyPlan]