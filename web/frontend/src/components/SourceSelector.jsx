import CustomSelect from "./CustomSelect.jsx";
import "./SourceSelector.css";

// Shared "Any Topic / From a Document" source picker, first built for
// Flashcards and reused by Quiz and Study Roadmap so all three look and
// behave the same. Helpers live in sourceSelection.js.

export default function SourceSelector({
  mode,
  onModeChange,
  documents = [],
  selectedDocumentId = "",
  onSelectDocument,
  disabled = false,
}) {
  const options =
    documents.length > 0
      ? documents.map((d) => ({ value: d.id, label: d.filename }))
      : [{ value: "", label: "No documents uploaded yet" }];

  return (
    <div className="source-selector">
      <div className="source-selector-tabs" role="group" aria-label="Generate from">
        <button
          type="button"
          className={`source-selector-tab ${mode === "topic" ? "active" : ""}`}
          aria-pressed={mode === "topic"}
          onClick={() => onModeChange("topic")}
          disabled={disabled}
        >
          Any Topic
        </button>
        <button
          type="button"
          className={`source-selector-tab ${mode === "document" ? "active" : ""}`}
          aria-pressed={mode === "document"}
          onClick={() => onModeChange("document")}
          disabled={disabled}
        >
          From a Document
        </button>
      </div>

      {mode === "document" && (
        <div className="source-selector-doc">
          <span className="source-selector-label">Choose Document:</span>
          <CustomSelect
            className="source-selector-doc-select"
            value={selectedDocumentId}
            onChange={onSelectDocument}
            options={options}
            disabled={disabled || documents.length === 0}
            title="Select a document"
          />
        </div>
      )}
    </div>
  );
}
