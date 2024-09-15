[![Current Release](https://img.shields.io/github/release/hairingx/aula/all.svg?style=plastic)](https://github.com/hairingx/aula/releases) [![Github All Releases](https://img.shields.io/github/downloads/hairingx/aula/total.svg?style=plastic)](https://github.com/hairingx/aula/releases)
<!-- [![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=plastic)](https://github.com/hacs/integration) -->

# Aula

This is a custom component for Home Assistant to integrate Aula.

- Installable and updatable via HACS
- UI config flow
- School schedules as Home Assistant calendars
- "Ugeplaner/Ugenoter" from "Min Uddannelse", "Meebook" and "EasyIQ"
- "Opgaver" from "Min Uddannelse"
- Messages - if there are unread messages, we turn a binary sensor on and populate it with the message details.
- "Huskelisten" from "Systematic"
- Use the builtin service to interact directly with Aulas API.

  "Ugeplaner/ugenoter/huskelisten" are stored as sensor attributes. Can be rendered like:

  ```yaml
  {{ state_attr("sensor.hojelse_skole_emilie", "ugeplan") }}
  ```

  And visualized in your dashboard with the markdown card:

  ```yaml
  type: markdown
  content: '{{ state_attr("sensor.hojelse_skole_emilie", "ugeplan") }}'
  title: Ugeplan for Emilie
  ```

  Another example using vertical-stack and collapsable-cards:

  ![image](https://user-images.githubusercontent.com/8055470/200306258-1c9e98ff-75d9-4111-994c-a69833e40c61.png)

```yaml
type: vertical-stack
cards:
  - type: custom:collapsable-cards
    title: Ugeplan Emilie
    cards:
      - type: markdown
        content: '{{ state_attr("sensor.hojelse_skole_emilie", "ugeplan") }}'
  - type: custom:collapsable-cards
    title: Ugeplan Emilie, næste uge
    cards:
      - type: markdown
        content: '{{ state_attr("sensor.hojelse_skole_emilie", "ugeplan_next") }}'
  - type: custom:collapsable-cards
    title: Ugeplan Rasmus
    cards:
      - type: markdown
        content: '{{ state_attr("sensor.hojelse_skole_rasmus", "ugeplan") }}'
  - type: custom:collapsable-cards
    title: Ugeplan Rasmus, næste uge
    cards:
      - type: markdown
        content: '{{ state_attr("sensor.hojelse_skole_rasmus", "ugeplan_next") }}'
```

   ![image](https://user-images.githubusercontent.com/8055470/199254249-3bf441bc-7dce-4f5d-a809-d119d20a7b2b.png)

- Lots of small fixes and optimizations

## Installation

#### HACS

- Ensure that HACS is installed.
- Add the Custom Repository: https://github.com/HairingX/aula.git
- Search for and install the "Aula" integration. (there might be 2 instances, pick the one with author: hairingx)
- Restart Home Assistant.
