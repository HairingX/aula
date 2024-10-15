from datetime import datetime, date, time
import re
import logging
from typing import Any, List, TypeVar
from homeassistant.util.dt import now

_LOGGER = logging.getLogger(__name__)

class AulaParser:
    """
    AulaParser provides methods to parse various general types of values, including strings, integers, booleans, dates, times, and datetimes.
    """

    _library_icon_regex = re.compile(r"library")
    _outdoor_icon_regex = re.compile(r"outdoor|outside|playground|slide|swing")
    _animals_icon_regex = re.compile(r"pets|animals")
    _cycling_icon_regex = re.compile(r"cycling|cykling")
    _gymnastics_icon_regex = re.compile(r"gymnastic|sports.*hall")
    _theater_icon_regex = re.compile(r"theater")
    _walking_icon_regex = re.compile(r"walking")
    _skateboard_icon_regex = re.compile(r"skateboard")
    _hammer_icon_regex = re.compile(r"hammer")
    _scissor_icon_regex = re.compile(r"scissor")
    _books_icon_regex = re.compile(r"books")
    _swim_icon_regex = re.compile(r"swim")
    _pens_icon_regex = re.compile(r"pens")
    _painting_icon_regex = re.compile(r"paint|brush")
    _football_icon_regex = re.compile(r"ball")
    _fire_icon_regex = re.compile(r"fire")
    _skating_icon_regex = re.compile(r"ice")

    @staticmethod
    def _parse_nullable_icon_str(value: Any) -> str | None:
        if value is None: return None
        result = str(value)
        # ordered on purpose, most explicit first, least explicit last
        if AulaParser._library_icon_regex.search(result): return "mdi:library"
        if AulaParser._outdoor_icon_regex.search(result): return "mdi:slide"
        if AulaParser._animals_icon_regex.search(result): return "mdi:paw"
        if AulaParser._cycling_icon_regex.search(result): return "mdi:bike"
        if AulaParser._gymnastics_icon_regex.search(result): return "mdi:gymnastics"
        if AulaParser._theater_icon_regex.search(result): return "mdi:theater"
        if AulaParser._walking_icon_regex.search(result): return "mdi:walk"
        if AulaParser._skateboard_icon_regex.search(result): return "mdi:skateboard"
        if AulaParser._hammer_icon_regex.search(result): return "mdi:hammer"
        if AulaParser._scissor_icon_regex.search(result): return "mdi:content-cut"
        if AulaParser._books_icon_regex.search(result): return "mdi:bookshelf"
        if AulaParser._swim_icon_regex.search(result): return "mdi:swim"
        if AulaParser._pens_icon_regex.search(result): return "mdi:lead-pencil"
        if AulaParser._painting_icon_regex.search(result): return "mdi:brush"
        if AulaParser._football_icon_regex.search(result): return "mdi:soccer"
        if AulaParser._fire_icon_regex.search(result): return "mdi:campfire"
        if AulaParser._skating_icon_regex.search(result): return "mdi:skate"
        return None

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        if isinstance(value, bool): return value
        return value == True

    @staticmethod
    def _parse_nullable_bool(value: Any) -> bool | None:
        if value is None: return None
        if isinstance(value, bool): return value
        return value == True

    @staticmethod
    def _parse_int(value: Any) -> int:
        if value is None: return -1
        if isinstance(value, int): return value
        return int(value)

    @staticmethod
    def _parse_int_list(value: Any) -> List[int]:
        if value and isinstance(value, list):
            if isinstance(value[0], int):
                return [int(val) for val in value] # type: ignore
        return list[int]()

    @staticmethod
    def _parse_nullable_int(value: Any) -> int | None:
        if value is None: return None
        if isinstance(value, int): return value
        return int(value)

    @staticmethod
    def _parse_str(value: Any) -> str:
        if value is None: return ""
        return str(value)

    @staticmethod
    def _parse_nullable_str(value: Any) -> str | None:
        if value is None: return None
        return str(value)

    @staticmethod
    def _parse_time(value: Any, fix_timezone: bool) -> time:
        newval = AulaParser._parse_nullable_time(value, fix_timezone)
        if newval is None: return time.min
        return newval

    @staticmethod
    def _parse_nullable_time(value: Any, fix_timezone: bool) -> time | None:
        if value is None: return None
        if isinstance(value, time): return value
        if isinstance(value, datetime): return value.time()
        value = value.split("T")[-1] # remove date part if present
        result = time.fromisoformat(value)
        if fix_timezone: return AulaParser._fix_timezone(result)
        return result

    @staticmethod
    def _parse_date(value: Any) -> date:
        newval = AulaParser._parse_nullable_date(value)
        if newval is None: return date.min
        return newval

    @staticmethod
    def _parse_nullable_date(value: Any) -> date | None:
        if value is None: return None
        if isinstance(value, date): return value
        if isinstance(value, datetime): return value.date()
        value = value.split("T")[0] # remove time part if present
        return date.fromisoformat(value)

    @staticmethod
    def _parse_datetime(value: Any, fix_timezone: bool) -> datetime:
        """
        args:
        - value: the value to parse
        - fix_timezone: whether to fix the timezone or not (Aula sometimes send timezone +00:00 for dates which has timezone corrected time)
        """
        newval = AulaParser._parse_nullable_datetime(value, fix_timezone)
        if newval is None: return datetime.min
        return newval

    @staticmethod
    def _parse_nullable_datetime(value: Any, fix_timezone: bool) -> datetime | None:
        if value is None: return None
        if isinstance(value, datetime): return value
        if isinstance(value, date): return datetime.combine(value, time.min)
        if not "T" in value: # no time part in the value
            parsed_date = AulaParser._parse_nullable_date(value)
            if not parsed_date: return None
            return datetime.combine(parsed_date, time.min)
        result = datetime.fromisoformat(value)
        if fix_timezone: return AulaParser._fix_timezone(result)
        return result.astimezone(now().tzinfo)

    TIME_TYPE = TypeVar("TIME_TYPE", datetime, time)
    @staticmethod
    def _fix_timezone(value: TIME_TYPE) -> TIME_TYPE:
        """
        Aula always send timezone +00:00, therefore we correct it here to HA configured timezone
        (assuming the HA instance is at same timezone as the Aula institution)
        """
        if isinstance(value, datetime):
            return now().replace(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute, second=value.second, microsecond=value.microsecond)
        # value is time
        return now().time().replace(hour=value.hour, minute=value.minute, second=value.second, microsecond=value.microsecond)
