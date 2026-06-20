import pytest
from expects import equal, expect, raise_error

from src.common.application.helpers.webhooks.url_validation import (
    InvalidWebhookUrlError,
    validate_webhook_url,
)


def test_validate_webhook_url__accepts_public_https():
    url = "https://hooks.example.com/doxiq"

    expect(validate_webhook_url(url)).to(equal(url))


@pytest.mark.parametrize(
    "url",
    [
        "http://hooks.example.com/x",  # not https
        "https://localhost/x",  # localhost
        "https://127.0.0.1/x",  # loopback
        "https://10.0.0.5/x",  # private 10/8
        "https://192.168.1.10/hook",  # private 192.168/16
        "https://169.254.1.1/x",  # link-local
    ],
)
def test_validate_webhook_url__rejects_unsafe(url):
    expect(lambda: validate_webhook_url(url)).to(raise_error(InvalidWebhookUrlError))
