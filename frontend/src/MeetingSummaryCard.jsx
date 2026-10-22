import { useState } from "react";

/**
 * Format markdown inline syntax: **bold**, *italic*, `code`
 */
function renderFormattedInline(text) {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="mom-strong">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

/**
 * Parse structured sections from meeting summary text:
 * Discussion, Decisions, Action Items, Owners, Deadlines
 */
function parseMeetingSummary(rawText) {
  if (!rawText) return null;

  const lines = rawText.split("\n");
  const sections = {
    discussion: [],
    decisions: [],
    actionItems: [],
    owners: [],
    deadlines: [],
    other: [],
  };

  let currentSection = "other";

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    const lower = trimmed.toLowerCase();
    // Detect section headers (###, **, plain)
    if (lower.includes("decision")) {
      currentSection = "decisions";
      continue;
    } else if (lower.includes("action item")) {
      currentSection = "actionItems";
      continue;
    } else if (lower.includes("owner")) {
      currentSection = "owners";
      continue;
    } else if (lower.includes("deadline")) {
      currentSection = "deadlines";
      continue;
    } else if (lower.includes("discussion")) {
      currentSection = "discussion";
      continue;
    }

    // Clean leading bullet markers
    const cleanItem = trimmed.replace(/^[-*•]\s+/, "").replace(/^\d+\.\s+/, "");

    if (currentSection in sections) {
      sections[currentSection].push(cleanItem);
    } else {
      sections.other.push(cleanItem);
    }
  }

  return sections;
}

export default function MeetingSummaryCard({ summaryText }) {
  const [copied, setCopied] = useState(false);
  const parsed = parseMeetingSummary(summaryText);

  function handleCopy() {
    navigator.clipboard.writeText(summaryText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  // Cross-reference Action Items, Owners, Deadlines into structured table rows
  const tableRows = [];
  if (parsed && (parsed.actionItems.length > 0 || parsed.owners.length > 0)) {
    const maxLen = Math.max(
      parsed.actionItems.length,
      parsed.owners.length,
      parsed.deadlines.length
    );

    for (let i = 0; i < maxLen; i++) {
      let task = parsed.actionItems[i] || `Deliverable #${i + 1}`;
      let owner = "Team";
      let deadline = "Pending Review";

      if (task.includes(":")) {
        const parts = task.split(":");
        task = parts[0].trim();
        owner = parts.slice(1).join(":").trim();
      } else if (parsed.owners[i]) {
        const oParts = parsed.owners[i].split(":");
        owner = oParts.length > 1 ? oParts[1].trim() : parsed.owners[i];
      }

      if (parsed.deadlines[i]) {
        const dParts = parsed.deadlines[i].split(":");
        deadline = dParts.length > 1 ? dParts[1].trim() : parsed.deadlines[i];
      }

      tableRows.push({ task, owner, deadline });
    }
  }

  return (
    <div className="mom-card full-block-card">
      <div className="mom-header">
        <div className="mom-title-group">
          <span className="mom-icon">📋</span>
          <div>
            <h4 className="mom-title">Minutes of Meeting (MoM)</h4>
            <span className="mom-subtitle">Executive Summary &amp; Action Registry</span>
          </div>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className="mom-copy-btn"
          title="Copy full minutes to clipboard"
        >
          {copied ? "✓ Copied!" : "📋 Copy Summary"}
        </button>
      </div>

      <div className="mom-body">
        {/* Key Decisions Agreed */}
        {parsed?.decisions?.length > 0 && (
          <div className="mom-section mom-decisions-box">
            <div className="mom-section-title">
              <span>🎯</span> Key Decisions Agreed
            </div>
            <ul className="mom-list">
              {parsed.decisions.map((item, idx) => (
                <li key={idx} className="mom-decision-item">
                  {renderFormattedInline(item)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Discussion Topics */}
        {parsed?.discussion?.length > 0 && (
          <div className="mom-section">
            <div className="mom-section-title">
              <span>💬</span> Discussion Points
            </div>
            <ul className="mom-list">
              {parsed.discussion.map((item, idx) => (
                <li key={idx} className="mom-list-item">
                  {renderFormattedInline(item)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Action Items Matrix / Corporate Table */}
        {tableRows.length > 0 ? (
          <div className="mom-section">
            <div className="mom-section-title">
              <span>⚡</span> Action Items &amp; Ownership Matrix
            </div>
            <div className="mom-table-wrapper">
              <table className="mom-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Action Item / Deliverable</th>
                    <th>Assignee / Owner</th>
                    <th>Target Due Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row, idx) => (
                    <tr key={idx}>
                      <td className="mom-td-num">{idx + 1}</td>
                      <td className="mom-td-task">
                        <strong>{renderFormattedInline(row.task)}</strong>
                      </td>
                      <td>
                        <span className="mom-owner-pill">
                          👤 {renderFormattedInline(row.owner)}
                        </span>
                      </td>
                      <td>
                        <span className="mom-deadline-pill">
                          📅 {renderFormattedInline(row.deadline)}
                        </span>
                      </td>
                      <td>
                        <span className="mom-status-badge">Assigned</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="mom-section">
            <div className="mom-raw-clean">
              {summaryText.split("\n").map((line, idx) => (
                <p key={idx} className="mom-line-p">
                  {renderFormattedInline(line)}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
