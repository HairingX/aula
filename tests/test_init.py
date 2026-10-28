"""Tests of setting up and removing an entry."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aula import AULA_CONNECT_URL, REPLACED_BY_AULA_CONNECT
from custom_components.aula.const import DOMAIN

DATA: dict[str, Any] = {
    "mitid_username": "parent",
    "auth_method": "APP",
    "access_token": "access",
    "refresh_token": "refresh",
    "token_expires_at": 1.0,
}


@pytest.fixture
def offline() -> Iterator[None]:
    """Setup without reaching Aula: no first refresh, no platforms."""
    with (
        patch("custom_components.aula.AulaDataCoordinator.async_config_entry_first_refresh", AsyncMock()),
        patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", AsyncMock()),
        patch("homeassistant.config_entries.ConfigEntries.async_unload_platforms", AsyncMock(return_value=True)),
    ):
        yield


def add_entry(hass: HomeAssistant, unique_id: str) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=unique_id, title=unique_id, data=DATA, version=2)
    entry.add_to_hass(hass)
    return entry


@pytest.mark.usefixtures("offline")
async def test_setting_up_an_entry_says_aula_connect_replaces_the_integration(hass: HomeAssistant) -> None:
    entry = add_entry(hass, "Aula")
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    issue = ir.async_get(hass).async_get_issue(DOMAIN, REPLACED_BY_AULA_CONNECT)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert not issue.is_fixable
    assert issue.learn_more_url == AULA_CONNECT_URL
    assert issue.translation_placeholders == {"url": AULA_CONNECT_URL}


@pytest.mark.usefixtures("offline")
async def test_the_notice_stays_until_the_last_entry_is_removed(hass: HomeAssistant) -> None:
    first, second = add_entry(hass, "Aula"), add_entry(hass, "Aula 2")
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    registry = ir.async_get(hass)

    await hass.config_entries.async_remove(first.entry_id)
    assert registry.async_get_issue(DOMAIN, REPLACED_BY_AULA_CONNECT) is not None

    await hass.config_entries.async_remove(second.entry_id)
    assert registry.async_get_issue(DOMAIN, REPLACED_BY_AULA_CONNECT) is None
