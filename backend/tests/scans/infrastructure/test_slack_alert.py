"""Infra tests for the Slack incoming-webhook alert sender
(08-ranking-watchlists §5.1). HTTP is mocked; no network, no signing."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from expects import be_false, be_true, contain, equal, expect, have_key

from src.scans.domain.models.finding import FindingRecord
from src.scans.infrastructure.alerts.render import build_alert_payload
from src.scans.infrastructure.services.slack_alert import post_slack_alert


def _payload():
    crit = FindingRecord(
        uuid=uuid4(), scan_id=uuid4(), site_id=uuid4(),
        source="owasp", tool="nuclei", category="A05", title="Exposed admin",
        severity="critical", confidence="alta", description="d",
        evidence={"raw_request": "SECRET EXPLOIT PAYLOAD"},  # must NOT leak
        impact="Full takeover", remediation="r", status="open", dedupe_key="dk",
    )
    return build_alert_payload(
        hostname="x.gob.mx", previous_grade="B", current_grade="F",
        grade_dropped=True, new_criticals=[crit],
    )


def _mock_client(status_code=200, raises=None):
    client = MagicMock()
    if raises is not None:
        client.post = AsyncMock(side_effect=raises)
    else:
        response = MagicMock()
        response.status_code = status_code
        client.post = AsyncMock(return_value=response)
    return client


async def test_slack_posts_plain_text_json_without_signature_headers():
    client = _mock_client(status_code=200)
    result = await post_slack_alert(
        webhook_url="https://hooks.slack.com/x", payload=_payload(), client=client
    )

    expect(result.delivered).to(be_true)
    _, kwargs = client.post.call_args
    # Plain {"text": ...} body, no signing headers.
    expect(kwargs["json"]).to(have_key("text"))
    expect(kwargs.get("headers")).to(equal(None))


async def test_slack_payload_is_redacted_no_raw_evidence():
    client = _mock_client(status_code=200)
    await post_slack_alert(
        webhook_url="https://hooks.slack.com/x", payload=_payload(), client=client
    )
    _, kwargs = client.post.call_args
    text = kwargs["json"]["text"]
    expect(text).to(contain("x.gob.mx"))
    expect(text).to(contain("Exposed admin"))
    # The raw exploit payload from evidence must never appear.
    assert "SECRET EXPLOIT PAYLOAD" not in text


async def test_slack_network_failure_returns_undelivered_without_raising():
    import httpx

    client = _mock_client(raises=httpx.ConnectError("boom"))
    result = await post_slack_alert(
        webhook_url="https://hooks.slack.com/x", payload=_payload(), client=client
    )
    expect(result.delivered).to(be_false)


async def test_slack_non_2xx_is_undelivered():
    client = _mock_client(status_code=500)
    result = await post_slack_alert(
        webhook_url="https://hooks.slack.com/x", payload=_payload(), client=client
    )
    expect(result.delivered).to(be_false)
    expect(result.status_code).to(equal(500))
