[![Current Release](https://img.shields.io/github/release/hairingx/aula/all.svg?style=plastic)](https://github.com/hairingx/aula/releases) [![Github All Releases](https://img.shields.io/github/downloads/hairingx/aula/total.svg?style=plastic)](https://github.com/hairingx/aula/releases)
<!-- [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration) -->

# Aula

This is a custom component for Home Assistant to integrate Aula.

Available entities:
- Calendars:
  - Events (Containing calendar events from aula, such as class rooms etc.)
  - Weekly Plan (containing meebook weekly plan)
  - Birthdays
- Sensors:
  - Presence (Present/Not Present)
  - Status (Detailed Presence, with state attribute on where the kid are on the school)
  - Present Duration (Time between check-in and check-out)
- Binary Sensors:
  - Unread Calendar Event
  - Unread Message (state attibutes with preview of the content and sender)
  - Unread Gallery (photos/videos)
  - Unread Post


Not yet implemented:

_As i have no json from the requests for these, i cannot develop and test the functionality to a point where i can verify their functionality._
- "Ugeplaner/Ugenoter" from "Min Uddannelse", "Meebook" and "EasyIQ"
- "Opgaver" from "Min Uddannelse"
- "Huskelisten" from "Systematic"


## Installation

#### HACS

- Ensure that HACS is installed.
- Add the Custom Repository: https://github.com/HairingX/aula.git
- Search for and install the "Aula" integration. (there might be 2 instances, pick the one with author: hairingx)
- Restart Home Assistant.

## Background: Aula Reworked
The original repository was great to get Aula into HomeAssistant.

As i started integrating it into my dashboards, I quickly learned that in order to get the setup i wanted, I would have to rewrite the solution.

Therefore I rewrote the integration to get the dashboard options i needed to create my dashboards

## Dashboard Examples
As my dashboard is not yet completed, this is just a dashboard from my test setup to test the different features.

### Custom Dashboard
In the top badge-bar i have (from left)
- Binary sensor Unread Post
- Binary sensor Unread Calendar Event
- Binary sensor Unread Gallery
- Binary sensor Unread Message (displaying the subject when active)
- Sensor Status (displaying the location if aula specifiec the location)
- Sensor Present Duration (displaying the time the kid has been present for the day)

Below the badge-bar i have a Calendar card, displaying events from Aula Calendar, Weekplan, birthdays and my local school calendar for custom items such as playdates etc.

Below that I have the weekplan. On the left side is the current days plan and on the right the current and next week can be accessed

Below the weekplan I have a graph for the Sensor Present Duration, and below that a section displaying details on the unread binary sensors.

![alt text](https://github.com/user-attachments/assets/712185a2-0f49-4c87-a148-4d2fbf714290)


### Calendar Dashboard
As the integration does not limit the interval for calendar data, the calenar dashboard can display data as far in the past/future as Aula supports, making it easy to get a larger overview
![Screenshot 2024-10-16 171901](https://github.com/user-attachments/assets/31e546c9-f1e6-44e8-8bea-e533138a0259)