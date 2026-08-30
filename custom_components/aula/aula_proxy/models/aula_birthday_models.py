from dataclasses import dataclass
from datetime import date
from typing import List

@dataclass
class AulaBirthdayEvent:
    institution_profile_id: int
    birthday_date: date
    institution_code: str
    full_name: str
    main_group_name: str
    """Group this child mainly belongs to. E.g. "0A"."""
    related_children_ids: List[int]
    """instProfileIds (== AulaChildProfile.id) of YOUR children this birthday relates to —
    the child(ren) of yours who share a group/hold with the birthday child. Aula's own
    combined calendar uses this field for its per-child toggle, so a birthday shared by a
    group both of your children are on relates to both and appears in both calendars."""
