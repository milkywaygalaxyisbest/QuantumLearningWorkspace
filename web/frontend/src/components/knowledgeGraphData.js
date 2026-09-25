/**
 * knowledgeGraphData.js
 *
 * Pure helpers (no React, no DOM) that turn the Knowledge Graph API's
 * GET /graph response into the shape the interactive graph view needs.
 *
 * Why this layer exists — the API returns:
 *   nodes: document nodes only  { id, title, node_type, definition, source_document }
 *   edges: document AND topic edges { source_id, target_id, node_type, similarity,
 *                                     label, relationship_type, source_title, target_title }
 *
 * Topic edges point at chunk ids ("<documentId>_<chunkIndex>") that are
 * NOT in the nodes list, and a graph renderer fails on edges whose
 * endpoints don't exist. So topic nodes are derived here from the edges.
 *
 * Page / section fields are read if the backend ever sends them
 * (page, page_number, section) and are simply empty until then.
 */

export const RELATIONSHIP_META = {
  prerequisite_of: { label: "Prerequisite of", color: "#d97706", arrow: "target" },
  example_of: { label: "Example of", color: "#059669", arrow: "source" },
  contrasts_with: { label: "Contrasts with", color: "#dc2626", arrow: "none" },
  related_to: { label: "Related to", color: "#7c8aa5", arrow: "none" },
};

export const KNOWN_RELATIONSHIP_TYPES = Object.keys(RELATIONSHIP_META);

export function prettifyType(type) {
  const text = String(type || "related_to").replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function relationshipMeta(type) {
  return RELATIONSHIP_META[type] || { label: prettifyType(type), color: "#64748b", arrow: "none" };
}

/**
 * How a relationship reads from one node's point of view.
 * Edge semantics come from relationship_classifier.py (A = source, B = target):
 *   prerequisite_of: A should be understood before B
 *   example_of:      B is an example of a concept from A
 */
export function describeRelationFrom(type, isSource) {
  switch (type) {
    case "prerequisite_of":
      return isSource ? "Prerequisite of" : "Builds on";
    case "example_of":
      return isSource ? "Illustrated by" : "Example of";
    case "contrasts_with":
      return "Contrasts with";
    case "related_to":
      return "Related to";
    default:
      return prettifyType(type);
  }
}

/** Full sentence for an edge, used in the edge detail view. */
export function describeEdge(edge, sourceTitle, targetTitle) {
  switch (edge.type) {
    case "prerequisite_of":
      return `${sourceTitle} should be understood before ${targetTitle}.`;
    case "example_of":
      return `${targetTitle} is an example of a concept from ${sourceTitle}.`;
    case "contrasts_with":
      return `${sourceTitle} and ${targetTitle} present differing ideas.`;
    case "related_to":
      return `${sourceTitle} and ${targetTitle} share a topic.`;
    default:
      return `${sourceTitle} → ${targetTitle}: ${prettifyType(edge.type)}.`;
  }
}

/** "shared terms: a, b, c" → ["a", "b", "c"] (same parsing the card view used). */
export function parseSharedTerms(label) {
  if (!label) return [];
  const prefix = "shared terms:";
  if (label.toLowerCase().startsWith(prefix)) {
    return label
      .slice(prefix.length)
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
  }
  return [label];
}

/** "<documentId>_<chunkIndex>" → { documentId, chunkIndex } (null if it doesn't match). */
export function parseTopicId(id) {
  const str = String(id || "");
  const idx = str.lastIndexOf("_");
  if (idx <= 0) return null;
  const chunkIndex = Number(str.slice(idx + 1));
  if (!Number.isInteger(chunkIndex) || chunkIndex < 0) return null;
  return { documentId: str.slice(0, idx), chunkIndex };
}

function edgeKey(layer, a, b) {
  const [x, y] = [a, b].sort();
  return `${layer}|${x}|${y}`;
}

/**
 * Normalizes the raw API response.
 * Returns { nodes, edges, nodeMap, documents }.
 *
 * Defensive rules (the backend already enforces 1 & 2, this just keeps
 * the renderer safe if older stored data slips through):
 *   1. self-links are dropped
 *   2. duplicate edges (either direction, same layer) are dropped
 *   3. edges pointing at documents that no longer exist are dropped
 *      (e.g. edges left over from a deleted document)
 */
export function normalizeGraph(raw) {
  const nodeMap = new Map();

  for (const n of raw?.nodes || []) {
    if (!n || !n.id) continue;
    const layer = n.node_type === "topic" ? "topic" : "document";
    const topic = layer === "topic" ? parseTopicId(n.id) : null;
    nodeMap.set(n.id, {
      id: n.id,
      title: n.title || "Untitled",
      layer,
      documentId: topic ? topic.documentId : n.id,
      chunkIndex: topic ? topic.chunkIndex : null,
      definition: n.definition || "",
      sourceDocument: n.source_document || n.title || "",
      page: n.page ?? n.page_number ?? null,
      section: n.section ?? null,
    });
  }

  function ensureTopicNode(id, fallbackTitle) {
    if (nodeMap.has(id)) return true;
    const parsed = parseTopicId(id);
    if (!parsed) return false;
    const parent = nodeMap.get(parsed.documentId);
    if (!parent) return false; // stale edge from a deleted document
    const docTitle = parent.title || fallbackTitle || "Untitled";
    nodeMap.set(id, {
      id,
      title: `${docTitle}, part ${parsed.chunkIndex + 1}`,
      layer: "topic",
      documentId: parsed.documentId,
      chunkIndex: parsed.chunkIndex,
      definition: "",
      sourceDocument: docTitle,
      page: null,
      section: null,
    });
    return true;
  }

  const edges = [];
  const seen = new Set();

  for (const e of raw?.edges || []) {
    const source = e?.source_id;
    const target = e?.target_id;
    if (!source || !target || source === target) continue;

    const layer = e.node_type === "topic" ? "topic" : "document";
    const key = edgeKey(layer, source, target);
    if (seen.has(key)) continue;

    if (layer === "topic") {
      if (!ensureTopicNode(source, e.source_title)) continue;
      if (!ensureTopicNode(target, e.target_title)) continue;
    } else if (!nodeMap.has(source) || !nodeMap.has(target)) {
      continue;
    }

    seen.add(key);
    edges.push({
      id: key,
      source,
      target,
      layer,
      type: e.relationship_type || "related_to",
      similarity: Number(e.similarity) || 0,
      label: e.label || "",
    });
  }

  const nodes = Array.from(nodeMap.values());
  const documents = nodes
    .filter((n) => n.layer === "document")
    .sort((a, b) => a.title.localeCompare(b.title));

  return { nodes, edges, nodeMap, documents };
}

/**
 * Applies the view filters. Returns { nodes, edges } to draw.
 *   layer:       "document" | "topic" | "all"
 *   hiddenTypes: Set of relationship types switched off
 *   documentId:  "all" or a document id — keeps that document's nodes
 *                plus everything directly connected to them
 */
export function filterGraph(graph, { layer, hiddenTypes, documentId }) {
  let nodes = graph.nodes.filter((n) => layer === "all" || n.layer === layer);
  const layerIds = new Set(nodes.map((n) => n.id));

  let edges = graph.edges.filter(
    (e) =>
      (layer === "all" || e.layer === layer) &&
      !hiddenTypes.has(e.type) &&
      layerIds.has(e.source) &&
      layerIds.has(e.target)
  );

  if (documentId && documentId !== "all") {
    const seed = new Set(nodes.filter((n) => n.documentId === documentId).map((n) => n.id));
    edges = edges.filter((e) => seed.has(e.source) || seed.has(e.target));
    const keep = new Set(seed);
    for (const e of edges) {
      keep.add(e.source);
      keep.add(e.target);
    }
    nodes = nodes.filter((n) => keep.has(n.id));
  }

  // Documents are real content and always shown; topic (chunk) nodes only
  // exist because of an edge, so hide them when none of their edges are visible.
  const connected = new Set();
  for (const e of edges) {
    connected.add(e.source);
    connected.add(e.target);
  }
  nodes = nodes.filter((n) => n.layer === "document" || connected.has(n.id));

  return { nodes, edges };
}

/** Relationships touching a node, from that node's point of view, strongest first. */
export function relatedConcepts(graph, nodeId) {
  return graph.edges
    .filter((e) => e.source === nodeId || e.target === nodeId)
    .map((e) => {
      const isSource = e.source === nodeId;
      const otherId = isSource ? e.target : e.source;
      return {
        edgeId: e.id,
        otherId,
        other: graph.nodeMap.get(otherId),
        type: e.type,
        phrase: describeRelationFrom(e.type, isSource),
        similarity: e.similarity,
      };
    })
    .filter((r) => r.other)
    .sort((a, b) => b.similarity - a.similarity);
}

/** Cheap fingerprint used to detect whether a background refresh changed anything. */
export function graphSignature(raw) {
  const nodes = (raw?.nodes || [])
    .map((n) => `${n.id}:${n.definition ? 1 : 0}`)
    .sort()
    .join(",");
  const edges = (raw?.edges || [])
    .map((e) => `${e.node_type}|${e.source_id}|${e.target_id}|${e.relationship_type}`)
    .sort()
    .join(",");
  return `${nodes}#${edges}`;
}

export function searchNodes(nodes, query, limit = 8) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const scored = [];
  for (const n of nodes) {
    const title = n.title.toLowerCase();
    let score = -1;
    if (title.startsWith(q)) score = 3;
    else if (title.includes(q)) score = 2;
    else if (n.definition.toLowerCase().includes(q)) score = 1;
    if (score >= 0) scored.push({ node: n, score });
  }
  scored.sort(
    (a, b) =>
      b.score - a.score ||
      (a.node.layer === b.node.layer ? 0 : a.node.layer === "document" ? -1 : 1) ||
      a.node.title.localeCompare(b.node.title)
  );
  return scored.slice(0, limit).map((s) => s.node);
}
