"""
Map the document a user selected in the UI to the id stored on its vector chunks.

The ingestion service generates its own document id for the chunks, which the
upload record keeps as `vector_document_id`, separate from the upload's own
`document_id`. The UI may send either of those, the Mongo `_id`, or only the
filename. Used by the chat and quiz proxies so both scope retrieval the same way.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from bson import ObjectId

from web.backend.database import get_uploads_collection

logger = logging.getLogger("uvicorn")


async def resolve_vector_document_id(
    user_id: str,
    document_id: Optional[str],
    filename: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (document_id_for_vector_search, filename).

    Only this user's upload records are searched, so another user's id is never
    translated. Falls back to what was sent if no matching record is found.
    """
    if not document_id and not filename:
        return None, None
    try:
        uploads = get_uploads_collection()
        match = None
        if document_id:
            candidates: List[Dict[str, Any]] = [
                {"vector_document_id": document_id},
                {"document_id": document_id},
            ]
            if ObjectId.is_valid(document_id):
                candidates.append({"_id": ObjectId(document_id)})
            match = await uploads.find_one({"user_id": user_id, "$or": candidates})
        if match is None and filename:
            match = await uploads.find_one(
                {"user_id": user_id, "filename": filename},
                sort=[("upload_date", -1)],
            )
        if match:
            resolved_id = match.get("vector_document_id") or match.get("document_id") or document_id
            return resolved_id, (match.get("filename") or filename)
    except Exception as e:
        logger.warning(f"Could not resolve selected document for scoping: {e}")
    return document_id, filename
