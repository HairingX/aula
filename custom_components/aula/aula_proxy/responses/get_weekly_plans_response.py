import datetime
from typing import List, TypedDict

class GetWeeklyPlansDailyTask(TypedDict):
    id: int
    type: str
    author: str
    group: str
    pill: str
    content: str
    editUrl: str

class GetWeeklyPlansDailyPlan(TypedDict):
    date: str
    tasks: List[GetWeeklyPlansDailyTask]

class GetWeeklyPlansResponse(TypedDict):
    id: int
    name: str
    unilogin: str
    from_date: datetime.date
    to_date: datetime.date
    weekPlan: List[GetWeeklyPlansDailyPlan]