import datetime
import re
from typing import Any, TypeVar
from homeassistant.util.dt import now

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
    def _parse_time(value: Any) -> datetime.time:
        if value is None: return datetime.time.min
        if isinstance(value, datetime.time): return value
        result = datetime.time.fromisoformat(value)
        AulaParser._fix_timezone(result)
        return result

    @staticmethod
    def _parse_nullable_time(value: Any) -> datetime.time | None:
        if value is None: return None
        if isinstance(value, datetime.time): return value
        result = datetime.time.fromisoformat(value)
        AulaParser._fix_timezone(result)
        return result

    @staticmethod
    def _parse_date(value: Any) -> datetime.date:
        if value is None: return datetime.date.min
        if isinstance(value, datetime.date): return value
        return datetime.date.fromisoformat(value)

    @staticmethod
    def _parse_nullable_date(value: Any) -> datetime.date | None:
        if value is None: return None
        if isinstance(value, datetime.date): return value
        return datetime.date.fromisoformat(value)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime.datetime:
        if value is None: return datetime.datetime.min
        if isinstance(value, datetime.datetime): return value
        result = datetime.datetime.fromisoformat(value)
        AulaParser._fix_timezone(result)
        return result

    @staticmethod
    def _parse_nullable_datetime(value: Any) -> datetime.datetime | None:
        if value is None: return None
        if isinstance(value, datetime.datetime): return value
        result = datetime.datetime.fromisoformat(value)
        AulaParser._fix_timezone(result)
        return result

    TIME_TYPE = TypeVar("TIME_TYPE", datetime.datetime, datetime.time)
    @staticmethod
    def _fix_timezone(value: TIME_TYPE) -> TIME_TYPE:
        """
        Aula always send timezone +00:00, therefore we correct it here to HA configured timezone
        (assuming the HA instance is at same timezone as the Aula institution)
        """
        if isinstance(value, datetime.datetime):
            return value.replace(tzinfo=now().tzinfo)
        # value is datetime.time
        return value.replace(tzinfo=now().tzinfo)
