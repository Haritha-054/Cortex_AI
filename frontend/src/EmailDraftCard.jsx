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
        <strong key={index} className="email-strong">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

/**
 * Parse an email draft string into subject, recipient, clean full-block body, and signoff.
 * Removes conversational clichés like "I hope this email finds you well".
 */
function parseEmailDraft(rawText) {
  if (!rawText) return { subject: "", cleanBody: "", to: "Team", closing: "Best regards," };

  let subject = "Meeting Follow-Up & Action Items";
  let workingText = rawText;

  // Extract Subject: line
  const subjectMatch = workingText.match(/(?:\*\*Subject:\*\*|Subject:)\s*([^\n\r]+)/i);
  if (subjectMatch) {
    subject = subjectMatch[1].replace(/^\*\*|\*\*$/g, "").trim();
    workingText = workingText.replace(/(?:\*\*Subject:\*\*|Subject:)\s*[^\n\r]+\n*/i, "").trim();
  }

  // Remove markdown **Body:** headers if present
  workingText = workingText.replace(/\*\*Body:\*\*\s*/i, "").trim();

  // Filter out cliché filler pleasantries requested by user
  workingText = workingText.replace(
    /^.*(?:hope (?:this (?:email|message) finds you well|you(?:'re| are) doing (?:well|good)|all is well|this finds you in good health)).*$/gim,
    ""
  );

  // Extract recipient greeting
  let to = "Team";
  const greetingMatch = workingText.match(/^(?:Dear|Hi|Hello)\s+([^,\n\r]+),?/im);
  if (greetingMatch) {
    to = greetingMatch[1].trim();
  }

  // Normalize multiple blank lines to clean double space between paragraphs
  const cleanBody = workingText.replace(/\n{3,}/g, "\n\n").trim();

  return { subject, cleanBody, to };
}

export default function EmailDraftCard({ emailDraft, senderId = "employee1" }) {
  const [copied, setCopied] = useState(false);
  const [copiedSubject, setCopiedSubject] = useState(false);
  const [viewRaw, setViewRaw] = useState(false);

  const { subject, cleanBody, to } = parseEmailDraft(emailDraft);

  function handleCopyAll() {
    navigator.clipboard.writeText(cleanBody);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function handleCopySubject() {
    navigator.clipboard.writeText(subject);
    setCopiedSubject(true);
    setTimeout(() => setCopiedSubject(false), 2000);
  }

  const mailtoHref = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(cleanBody)}`;

  // Split into clean paragraphs
  const paragraphs = cleanBody.split(/\n\s*\n/).filter((p) => p.trim());

  return (
    <div className="email-client-card">
      {/* Client Window Title Bar */}
      <div className="email-window-header">
        <div className="email-window-dots">
          <span className="window-dot dot-red"></span>
          <span className="window-dot dot-yellow"></span>
          <span className="window-dot dot-green"></span>
          <span className="email-window-title">
            ✉️ Microsoft Outlook / Executive Mail Preview (Full Block Style)
          </span>
        </div>
        <div className="email-window-actions">
          <button
            type="button"
            onClick={() => setViewRaw(!viewRaw)}
            className="email-btn-secondary"
            title="Toggle Raw / Formatted View"
          >
            {viewRaw ? "Formatted View" : "Raw Text"}
          </button>
          <button
            type="button"
            onClick={handleCopySubject}
            className="email-btn-secondary"
            title="Copy subject line"
          >
            {copiedSubject ? "✓ Subject Copied" : "Copy Subject"}
          </button>
          <button
            type="button"
            onClick={handleCopyAll}
            className="email-btn-primary"
            title="Copy complete email to clipboard"
          >
            {copied ? "✓ Copied Email!" : "📋 Copy Email"}
          </button>
          <a
            href={mailtoHref}
            target="_blank"
            rel="noopener noreferrer"
            className="email-btn-mailto"
            title="Open in Outlook / Mail app"
          >
            ↗ Open in Mail
          </a>
        </div>
      </div>

      {/* Full Block Style Metadata Header */}
      <div className="email-envelope">
        <div className="email-envelope-row">
          <span className="email-label">From:</span>
          <div className="email-val">
            <strong>{senderId}</strong> &lt;{senderId}@enterprise.internal&gt;
          </div>
        </div>
        <div className="email-envelope-row">
          <span className="email-label">To:</span>
          <div className="email-val">
            <span className="email-recipient-chip">👥 {to}</span>
          </div>
        </div>
        <div className="email-envelope-row email-subject-row">
          <span className="email-label">Subject:</span>
          <div className="email-subject-val">
            <span className="email-subject-text">{subject}</span>
            <span className="email-draft-tag">DRAFT • FULL BLOCK STYLE</span>
          </div>
        </div>
        <div className="email-envelope-row">
          <span className="email-label">Date:</span>
          <div className="email-val email-date-val">
            {new Date().toLocaleDateString(undefined, {
              weekday: "long",
              year: "numeric",
              month: "short",
              day: "numeric",
            })}
          </div>
        </div>
      </div>

      {/* FULL BLOCK FORMAT BODY (All elements flush left, no indentations) */}
      <div className="email-body-canvas full-block-canvas">
        {viewRaw ? (
          <pre className="email-raw-pre">{cleanBody}</pre>
        ) : (
          <div className="email-full-block-content">
            {paragraphs.map((p, pIdx) => {
              const lines = p.split("\n").filter((l) => l.trim());

              // Check if signature block
              const isSignoff =
                p.toLowerCase().includes("best regards") ||
                p.toLowerCase().includes("sincerely") ||
                p.toLowerCase().includes("warm regards") ||
                p.toLowerCase().includes("respectfully");

              if (isSignoff) {
                return (
                  <div key={pIdx} className="email-block-signoff">
                    <div className="signoff-close">{lines[0]}</div>
                    <div className="signoff-name">
                      {lines[1] ? lines[1].replace(/[\[\]]/g, "") : senderId}
                    </div>
                    {lines[2] && (
                      <div className="signoff-title">
                        {lines[2].replace(/[\[\]]/g, "")}
                      </div>
                    )}
                    <div className="signoff-company">
                      Enterprise AI Workspace &bull; Confidential
                    </div>
                  </div>
                );
              }

              // Check if bulleted/numbered action items list
              const isList = lines.some((l) =>
                /^[-*•\d+.]\s+/.test(l.trim()) || l.toLowerCase().includes("owner:") || l.toLowerCase().includes("deadline:")
              );

              if (isList) {
                return (
                  <div key={pIdx} className="email-block-action-list">
                    {lines.map((l, lIdx) => (
                      <div key={lIdx} className="email-block-action-item">
                        {renderFormattedInline(l.replace(/^[-*•]\s+/, ""))}
                      </div>
                    ))}
                  </div>
                );
              }

              // Standard Full Block paragraph
              return (
                <p key={pIdx} className="email-block-p">
                  {lines.map((line, lIdx) => (
                    <span key={lIdx} className="email-block-line">
                      {renderFormattedInline(line)}
                      {lIdx < lines.length - 1 && <br />}
                    </span>
                  ))}
                </p>
              );
            })}
          </div>
        )}
      </div>

      {/* Governance Footer */}
      <div className="email-footer-notice">
        <span>🛡️ Security Policy:</span> This email was generated in accordance with corporate
        Full Block communication standards. It remains an unsent draft until human review.
      </div>
    </div>
  );
}
