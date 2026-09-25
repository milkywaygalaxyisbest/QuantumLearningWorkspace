import { useEffect, useState } from "react";

// Helpers for the shared SourceSelector (Flashcards, Quiz, Study Roadmap).
// Kept out of SourceSelector.jsx so that file only exports a component
// (react-refresh/only-export-components).

// "linear_regression-notes.pdf" -> "linear regression notes"
export function cleanTopicFromFilename(filename) {
  if (!filename) return "";
  const withoutExt = filename.replace(/\.[^/.]+$/, "");
  return withoutExt.replace(/[_-]/g, " ").replace(/\s+/g, " ").trim();
}

// The upload whose Mongo id or document_id matches `id` (pages receive either).
export function findDocument(documents, id) {
  if (!id) return null;
  return documents.find((d) => String(d.id) === String(id) || String(d.document_id) === String(id)) || null;
}

// The signed-in user's uploaded documents (GET /uploads).
export function useUploadedDocuments(token) {
  const [documents, setDocuments] = useState([]);
  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    fetch(`${import.meta.env.VITE_API_BASE_URL}/uploads`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => {
        if (!cancelled && Array.isArray(data)) setDocuments(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [token]);
  return documents;
}
