import datetime
from typing import List, TypedDict

class AulaGetWeeklyPlansDailyTask(TypedDict):
    id: int
    type: str
    author: str
    group: str
    pill: str
    content: str

class AulaGetWeeklyPlansDailyPlan(TypedDict):
    date: str
    tasks: List[AulaGetWeeklyPlansDailyTask]

class AulaGetWeeklyPlansResponse(TypedDict):
    id: int
    name: str
    unilogin: str
    from_date: datetime.date
    to_date: datetime.date
    weekPlan: List[AulaGetWeeklyPlansDailyPlan]