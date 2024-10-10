[![Current Release](https://img.shields.io/github/release/hairingx/aula/all.svg?style=plastic)](https://github.com/hairingx/aula/releases) [![Github All Releases](https://img.shields.io/github/downloads/hairingx/aula/total.svg?style=plastic)](https://github.com/hairingx/aula/releases)
<!-- [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration) -->

# Aula

This is a custom component for Home Assistant to integrate Aula.

Available entities:
- Calendars:
  - Events (Containing calendar events from aula, such as class rooms etc.)
  - Weekly Plan (containing meebook weekly plan)
- Sensors:
  - Presence (Present/Not Present)
  - Status (Detailed Presence, with state attribute on where the kid are on the school)
  - Present Duration (Time between check-in and check-out)
- Binary Sensors:
  - Unread Calendar Event
  - Unread Message (state attibutes with preview of the content and sender)
  - Unread Gallery (photos/videos)


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
