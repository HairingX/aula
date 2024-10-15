from dataclasses import dataclass
from datetime import date

@dataclass
class AulaBirthdayEvent:
    institution_profile_id: int
    birthday_date: date
    institution_code: str
    full_name: str
