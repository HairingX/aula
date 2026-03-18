from collections import defaultdict
from datetime import datetime, timedelta, date, time
from typing import List

from ..responses.get_easyiq_weekplan_response import AulaEasyiqWeekplanEvent, AulaGetEasyiqWeekplanResponse

from .aula_easyiq_weekplan_models import AulaEasyiqWeeklyPlan, AulaEasyiqDailyPlan, AulaEasyiqEvent
from .aula_parser import AulaParser

EASYIQ_DATETIME_FORMAT = "%Y/%m/%d %H:%M"


class AulaEasyiqWeekplanParser(AulaParser):
    @staticmethod
    def parse_event(data: AulaEasyiqWeekplanEvent, child_user_id: str) -> AulaEasyiqEvent | None:
        start_str = data.get("start", "")
        end_str = data.get("end", "")
        try:
            start_dt = datetime.strptime(start_str, EASYIQ_DATETIME_FORMAT)
            end_dt = datetime.strptime(end_str, EASYIQ_DATETIME_FORMAT)
        except (ValueError, TypeError):
            return None

        item_type = AulaEasyiqWeekplanParser._parse_str(data.get("itemType"))
        if item_type == "5":
            title = AulaEasyiqWeekplanParser._parse_str(data.get("title"))
        else:
            title = AulaEasyiqWeekplanParser._parse_str(data.get("ownername"))

        task_id = hash(child_user_id + start_str + end_str + title)

        return AulaEasyiqEvent(
            id=task_id,
            title=title,
            description=AulaEasyiqWeekplanParser._parse_str(data.get("description")),
            owner_name=AulaEasyiqWeekplanParser._parse_str(data.get("ownername")),
            item_type=item_type,
            start_time=start_dt.time(),
            end_time=end_dt.time(),
        )

    @staticmethod
    def parse_events_as_weekly_plan(
        data: AulaGetEasyiqWeekplanResponse | None,
        child_name: str,
        child_user_id: str,
        from_date: date,
    ) -> AulaEasyiqWeeklyPlan:
        events_by_date: defaultdict[date, List[AulaEasyiqEvent]] = defaultdict(list)

        if data:
            events = data.get("Events", [])
            for event_data in events:
                event = AulaEasyiqWeekplanParser.parse_event(event_data, child_user_id)
                if event:
                    start_str = event_data.get("start", "")
                    try:
                        event_date = datetime.strptime(start_str, EASYIQ_DATETIME_FORMAT).date()
                    except (ValueError, TypeError):
                        continue
                    events_by_date[event_date].append(event)

        daily_plans: List[AulaEasyiqDailyPlan] = []
        for plan_date in sorted(events_by_date.keys()):
            daily_plans.append(AulaEasyiqDailyPlan(
                date=plan_date,
                events=events_by_date[plan_date],
            ))

        return AulaEasyiqWeeklyPlan(
            name=child_name,
            from_date=from_date,
            to_date=from_date + timedelta(days=6),
            daily_plans=daily_plans,
        )
