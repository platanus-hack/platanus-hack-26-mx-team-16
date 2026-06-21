"""Sites HTTP surface (12-api §1.1). Four routers:

- ``sites_router``     (``/sites``):    site detail + history
- ``ranking_router``   (``/ranking``):  public gov leaderboard
- ``watchlist_router`` (``/watchlist``):watchlist CRUD + monitor toggle
- ``me_router``        (``/me``):       account-level alert-channel prefs
"""

from fastapi import APIRouter

from src.sites.presentation.endpoints.add_watchlist import add_watchlist
from src.sites.presentation.endpoints.alerts_get import get_alerts
from src.sites.presentation.endpoints.alerts_put import put_alerts
from src.sites.presentation.endpoints.get_ranking import get_ranking
from src.sites.presentation.endpoints.get_site import get_site
from src.sites.presentation.endpoints.list_watchlist import list_watchlist
from src.sites.presentation.endpoints.remove_watchlist import remove_watchlist
from src.sites.presentation.endpoints.toggle_watchlist import toggle_watchlist

# --- Sites -------------------------------------------------------------------
sites_router = APIRouter(prefix="/sites", tags=["sites"])
sites_router.add_api_route(
    "/{site_id}",
    get_site,
    methods=["GET"],
    summary="Site detail: latest scan + history (public/owner)",
)

# --- Ranking -----------------------------------------------------------------
ranking_router = APIRouter(prefix="/ranking", tags=["ranking"])
ranking_router.add_api_route(
    "",
    get_ranking,
    methods=["GET"],
    summary="Public gov leaderboard (worst-first, cursor-paginated)",
)

# --- Watchlist ---------------------------------------------------------------
watchlist_router = APIRouter(prefix="/watchlist", tags=["watchlist"])
watchlist_router.add_api_route(
    "",
    list_watchlist,
    methods=["GET"],
    summary="List the current user's watched sites",
)
watchlist_router.add_api_route(
    "",
    add_watchlist,
    methods=["POST"],
    summary="Add a site to the watchlist → returns the created row (with id)",
)
watchlist_router.add_api_route(
    "/{watchlist_id}",
    toggle_watchlist,
    methods=["PATCH"],
    summary="Toggle monitoring on a watchlist row (owner-only)",
)
watchlist_router.add_api_route(
    "/{watchlist_id}",
    remove_watchlist,
    methods=["DELETE"],
    summary="Remove a watchlist row by its id (owner-only)",
)

# --- Me / alerts -------------------------------------------------------------
me_router = APIRouter(prefix="/me", tags=["me"])
me_router.add_api_route(
    "/alerts",
    get_alerts,
    methods=["GET"],
    summary="Get the current user's alert-channel prefs",
)
me_router.add_api_route(
    "/alerts",
    put_alerts,
    methods=["PUT"],
    summary="Upsert the current user's alert-channel prefs",
)
