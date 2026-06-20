"""Quórum de aprobación — lógica pura D-I (phases-config · F4)."""

from __future__ import annotations

import pytest
from expects import equal, expect

from src.workflows.domain.services.approval_quorum import (
    evaluate_quorum,
    quorum_pool_size,
    tally_votes,
)


# ── evaluate_quorum ──────────────────────────────────────────────────────────


def test_quorum__reached_when_approvals_meet_required():
    expect(evaluate_quorum(2, 0, 2, 3)).to(equal("approved"))


def test_quorum__default_single_approve_is_approved():
    # N=1, pool=1 (gate single de hoy): un approve ⇒ approved.
    expect(evaluate_quorum(1, 0, 1, 1)).to(equal("approved"))


def test_quorum__default_single_reject_is_rejected():
    # N=1, pool=1: un reject agota el pool ⇒ rejected (= hoy).
    expect(evaluate_quorum(0, 1, 1, 1)).to(equal("rejected"))


def test_quorum__reject_does_not_end_when_pool_still_reachable():
    # N=1 de un pool de 3: un reject deja 2 elegibles ⇒ aún pending (D-I).
    expect(evaluate_quorum(0, 1, 1, 3)).to(equal("pending"))


def test_quorum__fails_when_n_becomes_unreachable():
    # N=2, pool=3, 2 rechazos ⇒ solo 1 elegible queda ⇒ inalcanzable ⇒ rejected.
    expect(evaluate_quorum(0, 2, 2, 3)).to(equal("rejected"))


def test_quorum__pending_when_partial_and_reachable():
    expect(evaluate_quorum(1, 1, 2, 4)).to(equal("pending"))


# ── quorum_pool_size ─────────────────────────────────────────────────────────


def test_pool_size__designated_users_win():
    expect(quorum_pool_size(5, 2)).to(equal(5))


def test_pool_size__falls_back_to_required_when_no_users():
    expect(quorum_pool_size(0, 3)).to(equal(3))


# ── tally_votes ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("resolution", "expected"),
    [
        ({"approved": True}, (1, 0)),
        ({"approved": False}, (0, 1)),
        ({}, (0, 1)),
    ],
)
def test_tally__single_resolution_shape(resolution, expected):
    expect(tally_votes(resolution, distinct_approvers=True)).to(equal(expected))


def test_tally__multi_vote_counts_approvals_and_rejections():
    resolution = {"votes": [{"approved": True, "actor": "a"}, {"approved": False, "actor": "b"}]}

    expect(tally_votes(resolution, distinct_approvers=True)).to(equal((1, 1)))


def test_tally__distinct_dedups_last_vote_per_actor():
    resolution = {"votes": [{"approved": False, "actor": "a"}, {"approved": True, "actor": "a"}]}

    expect(tally_votes(resolution, distinct_approvers=True)).to(equal((1, 0)))


def test_tally__non_distinct_counts_every_vote():
    resolution = {"votes": [{"approved": False, "actor": "a"}, {"approved": True, "actor": "a"}]}

    expect(tally_votes(resolution, distinct_approvers=False)).to(equal((1, 1)))
