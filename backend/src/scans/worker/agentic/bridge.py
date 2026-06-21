"""``PlaywrightBridge`` — CAMINO A: the browser drives the chat conversation
(spec §3.2/§4, plan §4).

garak/promptfoo cannot discover the widget endpoint or the response shape on
their own (spec §3.1); there is no "give it a URL and attack the chat" mode. So
the bridge is **ours**: a real browser opens the page, resolves the lazy-loaded
widget (scroll + launcher click), types each payload into the chat ``<textarea>``,
submits, and reads the reply from the DOM. The browser keeps session, cookies,
``conversation_id`` and CSRF natively, which is what makes multi-turn (Crescendo)
work for free over any vendor.

CRITICAL: ``playwright`` is **lazy-imported inside the methods** — the backend
has no playwright in CI, so this module must import cleanly without it. Tests
inject a fake ``page``/``browser`` (or drive ``capture_dom`` / ``send_and_read``
against a mock), never a real browser.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from src.common.application.logging import get_logger
from src.scanning import assert_public_target

logger = get_logger(__name__)

#: Selectors used to find the chat input when no vendor selector is known.
_CHAT_INPUT_SELECTORS: tuple[str, ...] = (
    "textarea",
    "input[type='text']",
    "[contenteditable='true']",
    "[role='textbox']",
)

#: window.* globals probed via page.evaluate to feed the fingerprint pass.
_PROBED_GLOBALS: tuple[str, ...] = (
    "Intercom",
    "intercomSettings",
    "drift",
    "driftt",
    "$zopim",
    "zE",
    "zEmbed",
    "tidioChatApi",
    "$crisp",
    "lpTag",
    "HubSpotConversations",
    "fcWidget",
    "Tawk_API",
    "$zoho",
    "Kommunicate",
    "OpenAI",
)


@dataclass
class PageSnapshot:
    """An enriched DOM/network snapshot the detector classifies over (spec §2.2)."""

    dom: str
    network: list[Any] = field(default_factory=list)
    window_globals: list[str] = field(default_factory=list)
    location_url: str = ""


@dataclass
class PlaywrightBridge:
    """Opens the target, resolves the widget, and runs the chat turn-by-turn.

    Args:
        target: the URL to navigate to (egress-guarded unless allow-listed demo).
        cancel: the 04 ``CancelToken`` — checked between payloads by the caller.
        allowed_demo_hosts: opt-in allow-list so the planted bot on ``localhost``
            is reachable (``assert_public_target`` rejects loopback by default).
        page: an injected page (tests) — when set, no browser is launched.
    """

    target: str
    cancel: Any | None = None
    allowed_demo_hosts: frozenset[str] | None = None
    page: Any | None = None
    _browser: Any | None = field(default=None, repr=False)
    _playwright: Any | None = field(default=None, repr=False)
    _network: list[Any] = field(default_factory=list, repr=False)

    async def __aenter__(self) -> PlaywrightBridge:
        # Egress guard first — never navigate to a private/loopback host unless it
        # is explicitly allow-listed for the demo (the planted bot).
        assert_public_target(self.target, allowed_demo_hosts=self.allowed_demo_hosts)
        if self.page is None:
            await self._launch()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _launch(self) -> None:
        """Start Chromium and navigate to the target. ``playwright`` lazy-imported."""
        from playwright.async_api import async_playwright  # noqa: PLC0415 - lazy

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        context = await self._browser.new_context()
        self.page = await context.new_page()
        # Capture network so the fingerprint pass sees third-party widget hosts.
        self.page.on("request", lambda req: self._network.append(getattr(req, "url", "")))
        await self.page.goto(self.target, wait_until="domcontentloaded")

    async def close(self) -> None:
        """Tear the browser down (best-effort; never raises into the flow)."""
        try:
            if self._browser is not None:
                await self._browser.close()
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception:  # noqa: BLE001 - teardown must never break the scan
            logger.warning("agentic.bridge.close_failed")

    # -- detection-support ------------------------------------------------------

    async def capture_dom(self, *, resolve_lazy: bool = True) -> PageSnapshot:
        """Snapshot the DOM + network + window globals for the detector (spec §2.2).

        When ``resolve_lazy`` is set, the bridge waits for the network to settle,
        scrolls, clicks a generic launcher and re-snapshots — so a lazy-loaded
        widget is seen before detection decides "no AI".
        """
        if resolve_lazy:
            await self._resolve_lazy_load()
        dom = await self.page.content()
        globals_present = await self._probe_globals()
        return PageSnapshot(
            dom=dom,
            network=list(self._network),
            window_globals=globals_present,
            location_url=self.target,
        )

    async def _resolve_lazy_load(self) -> None:
        """Settle network → scroll → click a generic launcher (spec §2.2)."""
        try:
            await self.page.wait_for_load_state("networkidle")
        except Exception:  # noqa: BLE001 - networkidle can time out; proceed anyway
            pass
        try:
            await self.page.mouse.wheel(0, 10000)
        except Exception:  # noqa: BLE001
            pass
        from src.scans.worker.agentic.detector import GENERIC_LAUNCHER_SELECTORS

        await self.click_first(GENERIC_LAUNCHER_SELECTORS)

    async def _probe_globals(self) -> list[str]:
        """Return which of the probed ``window.*`` globals are defined."""
        present: list[str] = []
        for name in _PROBED_GLOBALS:
            try:
                defined = await self.page.evaluate(
                    f"() => typeof window['{name}'] !== 'undefined'"
                )
            except Exception:  # noqa: BLE001 - evaluate may fail on a hostile page
                defined = False
            if defined:
                present.append(name)
        return present

    async def click_first(self, selectors: Sequence[str]) -> bool:
        """Click the first selector that matches; ``True`` if one was clicked."""
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0:
                    await locator.click(timeout=2000)
                    return True
            except Exception:  # noqa: BLE001 - a missing/occluded launcher is fine
                continue
        return False

    # -- attack-bridge (CAMINO A) ----------------------------------------------

    async def open_widget(self, launcher_selectors: Sequence[str] | None = None) -> None:
        """Open the chat widget by clicking its launcher (vendor or generic)."""
        from src.scans.worker.agentic.detector import GENERIC_LAUNCHER_SELECTORS

        selectors = list(launcher_selectors or ()) + list(GENERIC_LAUNCHER_SELECTORS)
        await self.click_first(selectors)

    async def send_and_read(
        self, text: str, *, input_selectors: Sequence[str] | None = None
    ) -> str:
        """Type ``text`` into the chat input, submit, and read the reply text.

        Returns the new assistant reply (best-effort: the visible inner text of the
        widget after the turn). The browser carries the conversation state, so
        multi-turn sequences just call this repeatedly.
        """
        selectors = list(input_selectors or ()) + list(_CHAT_INPUT_SELECTORS)
        before = await self._widget_text()
        typed = False
        for selector in selectors:
            try:
                locator = self.page.locator(selector).first
                if await locator.count() > 0:
                    await locator.fill(text)
                    await locator.press("Enter")
                    typed = True
                    break
            except Exception:  # noqa: BLE001 - try the next candidate input
                continue
        if not typed:
            return ""
        await self._wait_for_reply(before)
        after = await self._widget_text()
        return _new_text(before, after)

    async def _wait_for_reply(self, before: str) -> None:
        """Wait until the widget text grows (a new reply arrived) or times out."""
        try:
            await self.page.wait_for_function(
                "(prev) => document.body.innerText.length > prev.length",
                arg=before,
                timeout=8000,
            )
        except Exception:  # noqa: BLE001 - no growth within the budget; read as-is
            pass

    async def _widget_text(self) -> str:
        try:
            return await self.page.inner_text("body")
        except Exception:  # noqa: BLE001
            return ""


def _new_text(before: str, after: str) -> str:
    """The portion of ``after`` that was not present in ``before`` (the reply)."""
    if after.startswith(before):
        return after[len(before):].strip()
    return after.strip()
