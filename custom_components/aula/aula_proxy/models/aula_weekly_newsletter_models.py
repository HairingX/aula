from dataclasses import dataclass
from typing import List

@dataclass
class AulaWeeklyNewsletter:
    indhold: str

@dataclass
class AulaWeeklyNewsletters:
    full_name: str
    first_name: str
    newsletters: List[AulaWeeklyNewsletter]