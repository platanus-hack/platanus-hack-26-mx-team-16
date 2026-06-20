"""Router for the Knowledge Base module."""

from fastapi import APIRouter

from src.knowledge_base.presentation.endpoints.kb_endpoints import (
    search_chunks,
    suggest_rules,
)
from src.knowledge_base.presentation.endpoints.workflow_kb.deleter import delete_kb_document
from src.knowledge_base.presentation.endpoints.workflow_kb.lister import list_kb_documents
from src.knowledge_base.presentation.endpoints.workflow_kb.uploader import upload_kb_document

knowledge_base_router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

knowledge_base_router.add_api_route(
    "/search",
    search_chunks,
    methods=["POST"],
    summary="Search KB chunks",
    description="Search similar chunks by query text using pgvector cosine similarity",
)

knowledge_base_router.add_api_route(
    "/suggest-rules",
    suggest_rules,
    methods=["POST"],
    summary="Suggest rules from KB",
    description="Generate business rule suggestions from KB context",
)

workflow_kb_router = APIRouter(tags=["Knowledge Base"])

workflow_kb_router.add_api_route(
    "/workflows/{workflow_id}/knowledge-base/documents",
    upload_kb_document,
    methods=["POST"],
    summary="Upload workflow KB document",
)
workflow_kb_router.add_api_route(
    "/workflows/{workflow_id}/knowledge-base/documents",
    list_kb_documents,
    methods=["GET"],
    summary="List workflow KB documents",
)
workflow_kb_router.add_api_route(
    "/workflows/{workflow_id}/knowledge-base/documents/{document_id}",
    delete_kb_document,
    methods=["DELETE"],
    summary="Delete workflow KB document",
)
