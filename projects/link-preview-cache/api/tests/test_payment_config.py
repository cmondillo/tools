"""Tests for the testnet-facilitator <-> CDP-facilitator switch.

This is the one piece of config wiring with no coverage elsewhere: everything
else in the suite runs with CDP credentials unset (the default), so nothing
exercises the branch that engages once CDP_API_KEY_ID/CDP_API_KEY_SECRET are
both present.
"""

from dataclasses import replace

from app.config import get_settings
from app.payment import _facilitator_config

_BASE_SETTINGS = get_settings()


def test_uses_plain_facilitator_url_when_cdp_credentials_are_unset():
    settings = replace(_BASE_SETTINGS, cdp_api_key_id=None, cdp_api_key_secret=None)

    assert settings.use_cdp_facilitator is False
    config = _facilitator_config(settings)

    assert config == {"url": settings.facilitator_url}


def test_switches_to_cdp_facilitator_once_both_credentials_are_set():
    settings = replace(
        _BASE_SETTINGS, cdp_api_key_id="fake-key-id", cdp_api_key_secret="fake-key-secret"
    )

    assert settings.use_cdp_facilitator is True
    config = _facilitator_config(settings)

    assert config["url"] == "https://api.cdp.coinbase.com/platform/v2/x402"
    assert callable(config["create_headers"])


def test_one_credential_alone_is_not_enough_to_switch():
    settings = replace(_BASE_SETTINGS, cdp_api_key_id="fake-key-id", cdp_api_key_secret=None)

    assert settings.use_cdp_facilitator is False
    assert _facilitator_config(settings) == {"url": settings.facilitator_url}
