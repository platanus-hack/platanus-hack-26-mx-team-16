import re
from dataclasses import dataclass
from typing import Self

from src.common.application.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConsumerClient:
    """
    This class parses the user agent for growth-supported clients
    The correct format for user-agent is:
    PLATFORM:(BUNDLE_ID|APPLICATION_ID)/VERSION_NAME:VERSION_CODE
    e.g: android:com.vnext.tenant/1.0.0-testing:1
    """

    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

    platform: str | None = None
    application_id: str | None = None
    version_name: str | None = None
    version_code: int | None = None

    VERSION_PATTERN = r"(android|ios|web):([a-z]|\.)*\/(\d|\.|-|[a-z])+:(\d|.)+"

    @classmethod
    def is_valid_agent(cls, agent: str):
        matched = re.match(cls.VERSION_PATTERN, agent)
        return bool(matched)

    @classmethod
    def build(cls, agent: str) -> Self | None:
        if not cls.is_valid_agent(agent):
            return None

        app_info, version_info = agent.split("/")
        platform, application_id = app_info.split(":")
        version_name, version_code = version_info.split(":")

        try:
            parse_version_code = int(version_code)
        except Exception as e:
            logger.error(
                "client.version_code.parse_failed",
                version_code=version_code,
                error=str(e),
                error_type=type(e).__name__,
            )
            parse_version_code = 1

        return cls(
            platform=platform,
            application_id=application_id,
            version_name=version_name,
            version_code=parse_version_code,
        )

    @property
    def is_mobile(self):
        return self.platform in [self.ANDROID, self.IOS]

    @property
    def is_web(self):
        return self.platform == self.WEB

    # TODO: implement a way to evaluate application_id to know if it a admin, user, or backoffice app
