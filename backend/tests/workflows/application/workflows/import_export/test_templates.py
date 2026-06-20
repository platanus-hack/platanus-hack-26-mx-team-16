"""Tests for the workflow templates catalog (E6 · W4)."""

from __future__ import annotations

import json

from expects import contain, equal, expect, have_keys

from src.workflows.application.workflows.import_export.templates import (
    TEMPLATES_DIR,
    WorkflowTemplatesLister,
)


def test_execute__lists_shipped_templates():
    # Act
    templates = WorkflowTemplatesLister().execute()

    # Assert — both seed templates are present with metadata + envelope.
    slugs = {t["slug"] for t in templates}
    expect(slugs).to(contain("pedidos-multicanal", "circular-judicial"))
    for t in templates:
        expect(t).to(have_keys("slug", "name", "description", "envelope"))
        expect(t["envelope"]["schemaVersion"]).to(equal("1.0"))


def test_execute__empty_when_dir_missing(tmp_path):
    # Arrange — a non-existent directory.
    missing = tmp_path / "nope"

    # Act
    templates = WorkflowTemplatesLister(templates_dir=missing).execute()

    # Assert
    expect(templates).to(equal([]))


def test_shipped_templates_are_valid_bundles():
    """Every shipped template parses and exposes the bundle contract."""
    for path in TEMPLATES_DIR.glob("*.json"):
        envelope = json.loads(path.read_text())
        expect(envelope).to(have_keys("schemaVersion", "workflow", "documentTypes", "pipeline", "rules"))
        expect(envelope["requiresConfiguration"]).to(contain("destinations", "sources"))
