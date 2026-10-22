"""Entry-scoped notices for local push migration and recovery."""

from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir

from custom_components.tapo.const import DOMAIN

ISSUE_TYPES = (
    "local_push_upgrade",
    "local_push_missing_devices",
    "local_push_unavailable",
)


@callback
def async_set_push_issue(hass, entry, issue_type, active):
    """Keep one actionable notice per issue type and hub entry."""
    issue_id = f"{issue_type}_{entry.entry_id}"
    if not active:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=issue_type == "local_push_upgrade",
        severity=ir.IssueSeverity.WARNING,
        translation_key=issue_type,
        translation_placeholders={
            "hub": getattr(entry, "title", "H100"),
            "integration_url": "/config/integrations/integration/tapo",
        },
    )


@callback
def async_clear_push_issues(hass, entry):
    """Remove only notices belonging to the removed hub entry."""
    for issue_type in ISSUE_TYPES:
        async_set_push_issue(hass, entry, issue_type, False)
