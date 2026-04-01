from dataclasses import dataclass
import datetime
from typing import List


@dataclass
class AulaNewsletter:
    """A weekly newsletter from MinUddannelse (ugebrev).

    id: Generated unique ID
    content_html: Raw HTML content from the API (preserved for custom card rendering)
    institution_name: Name of the institution that published the newsletter
    """
    id: str
    content_html: str
    institution_name: str


@dataclass
class AulaWeeklyNewsletter:
    """A collection of newsletters for one child for one week."""
    child_name: str
    from_date: datetime.date
    to_date: datetime.date
    newsletters: List[AulaNewsletter]
