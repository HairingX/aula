# from datetime import timedelta, date
# from typing import List

# from ..responses.get_weekly_newsletter_response import *
# from ..utils.list_utils import list_without_none

# from .aula_weekly_newsletter_models import *
# from .aula_parser import AulaParser

# class AulaWeeklyNewsletterParser(AulaParser):
#     @staticmethod
#     def parse_daily_plan_task(data: GetWeeklyPlansDailyTask | None) -> AulaDailyPlanTask:
#         if not data: raise ValueError()
#         result = AulaDailyPlanTask(
#             id = AulaWeeklyNewsletterParser._parse_int(data.get("id")),
#             type = AulaWeeklyNewsletterParser._parse_str(data.get("type")),
#             author = AulaWeeklyNewsletterParser._parse_str(data.get("author")),
#             group = AulaWeeklyNewsletterParser._parse_str(data.get("group")),
#             pill = AulaWeeklyNewsletterParser._parse_str(data.get("pill")),
#             content = AulaWeeklyNewsletterParser._parse_str(data.get("content")),
#             editUrl = AulaWeeklyNewsletterParser._parse_nullable_str(data.get("editUrl")),
#         )
#         return result

#     @staticmethod
#     def parse_daily_plan_tasks(data: List[GetWeeklyPlansDailyTask] | None) -> List[AulaDailyPlanTask]:
#         if data is None: return []
#         return list_without_none(map(AulaWeeklyNewsletterParser.parse_daily_plan_task, data))

#     @staticmethod
#     def parse_daily_plan(data: GetWeeklyPlansDailyPlan | None, date: date) -> AulaDailyPlan:
#         if not data: raise ValueError()
#         result = AulaDailyPlan(
#             date = date,
#             tasks = AulaWeeklyNewsletterParser.parse_daily_plan_tasks(data.get("tasks")),
#         )
#         return result

#     @staticmethod
#     def parse_daily_plans(data: List[GetWeeklyPlansDailyPlan] | None, from_date: date) -> List[AulaDailyPlan]:
#         if data is None: return []
#         result = list[AulaDailyPlan]()
#         for i, dayplan in enumerate(data):
#             plan_date = from_date + timedelta(days=i)
#             plan = AulaWeeklyNewsletterParser.parse_daily_plan(dayplan, plan_date)
#             if plan: result.append(plan)
#         return result

#     @staticmethod
#     def parse_profile(data: AulaWeeklyNewsletterPersonData | None) -> AulaWeeklyNewsletterProfile:
#         if not data: raise ValueError()
#         result = AulaWeeklyNewsletterProfile(
#             full_name = AulaWeeklyNewsletterParser._parse_str(data.get("navn")),
#             first_name = AulaWeeklyNewsletterParser._parse_str(data.get("navn").split(" ")[0]),
#             institutions = AulaWeeklyNewsletterParser.parse_institutions(data.get("institutioner")),
#         )
#         return result

#     @staticmethod
#     def parse_profiles(data: List[AulaWeeklyNewsletterPersonData] | None) -> List[AulaWeeklyNewsletterProfile]:
#         if data is None: return []
#         return list_without_none(map(AulaWeeklyNewsletterParser.parse_profile, data))


#     @staticmethod
#     def parse_weekly_newsletter_profile(data: AulaGetWeeklyNewsletterResponse | None) -> AulaWeeklyNewsletters|None:
#         if not data: raise ValueError()
#         personer = data.get("personer")
#         if personer is None: return None

#         for person in personer:
#             full_name = person["navn"]
#             first_name = full_name.split(" ")[0]

#             institutions = person.get("institutioner")
#             if institutions is None: continue
#             for institution in :

#         result = AulaWeeklyNewsletters(
#             full_name= AulaWeeklyNewsletterParser._parse_str(data.get("navn")),
#             profiles= AulaWeeklyNewsletterParser.parse_profiles(data.get("personer")),
#             from_date = AulaWeeklyNewsletterParser._parse_date(data.get("from_date")),
#             to_date = AulaWeeklyNewsletterParser._parse_date(data.get("to_date")),
#         )

#         return result

#     @staticmethod
#     def parse_weekly_newsletter_profiles(data: List[AulaGetWeeklyNewsletterResponse] | None) -> List[AulaWeeklyNewsletterProfiles]:
#         if data is None: return []
#         return list_without_none(map(AulaWeeklyNewsletterParser.parse_weekly_newsletter_profile, data))
