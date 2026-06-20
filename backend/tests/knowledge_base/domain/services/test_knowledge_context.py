"""F5 · B2 fix: knowledge_context hydration from a rule's knowledge_refs."""

from types import SimpleNamespace
from uuid import UUID, uuid4

from expects import equal, expect

from src.knowledge_base.domain.services.knowledge_context import build_knowledge_context

_TENANT = UUID("22222222-2222-2222-2222-222222222222")


class _FakeKBRepo:
    def __init__(self, docs):
        self._docs = docs

    async def find_by_id(self, document_id, tenant_id):
        return self._docs.get(document_id)


async def test_build_knowledge_context__shapes_resolvable_refs():
    ref = uuid4()
    repo = _FakeKBRepo({ref: SimpleNamespace(slug="drugs", file_name="drugs.csv", extracted_text="aspirin -> ASA")})

    context = await build_knowledge_context(repo, _TENANT, [ref])

    expect(context).to(equal([{"slug": "drugs", "title": "drugs.csv", "content": "aspirin -> ASA"}]))


async def test_build_knowledge_context__skips_missing_and_empty():
    present = uuid4()
    repo = _FakeKBRepo(
        {present: SimpleNamespace(slug="x", file_name="x", extracted_text="")}  # empty → skipped
    )

    context = await build_knowledge_context(repo, _TENANT, [present, uuid4()])

    expect(context).to(equal([]))
