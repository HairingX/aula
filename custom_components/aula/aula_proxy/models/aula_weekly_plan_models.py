from dataclasses import dataclass
import datetime
from typing import List, Optional

@dataclass
class AulaDailyPlanTask:
    """A task/entry in a daily plan from the Meebook weekly plan API.

    author: Author of the task (likely the teacher, but not always populated)
    content: The task content/description (in younger classes, often describes the day's work/activities)
    group: The class/group name. Freeform text, e.g. "1A", "1a matematik"
    id: Unique task ID
    pill: Subject label, e.g. "Matematik", "Dansk". Meebook-specific field. Empty string for other backends.
    type: Task type. Known values:
        - "task": An assignment that must be completed (shown with clock icon in Aula)
        - "comment": Informational comment (shown with info icon in Aula)
    editUrl: URL for editing the task in Meebook (optional)
    title: Task title, used for assignment-type tasks (optional)
    """
    author: str
    content: str
    group: str
    id: int
    pill: str
    type: str
    editUrl: Optional[str|None] = None
    title: Optional[str|None] = None

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