import { useState, useEffect } from 'react';
import VoiceRequest from './VoiceRequest';
import MeetingSummaryCard from './MeetingSummaryCard';
import EmailDraftCard from './EmailDraftCard';
import './App.css';

export default function App() {
  const [userId, setUserId] = useState('employee1');
  const [token, setToken] = useState('');
  const [role, setRole] = useState('employee');
  const [tokenLoading, setTokenLoading] = useState(false);
  const [tokenError, setTokenError] = useState('');
  
  const [meetingNotes, setMeetingNotes] = useState(
    'The team agreed to finish testing by Friday. Ravi will prepare the test report. Priya will fix the login bug. The next review is Monday.'
  );

  const [result, setResult] = useState(null);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalMessage, setApprovalMessage] = useState('');
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'mom', 'email', 'audit'

  // Fetch token in background seamlessly when user profile changes
  async function fetchTokenForUser(id) {
    setTokenLoading(true);
    setTokenError('');
    try {
      const res = await fetch('http://127.0.0.1:8000/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: id }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to authenticate');
      }
      setToken(data.access_token);
      setRole(data.role);
      return data.access_token;
    } catch (err) {
      setTokenError(err.message || 'Error authenticating user');
      return null;
    } finally {
      setTokenLoading(false);
    }
  }

  useEffect(() => {
    fetchTokenForUser(userId);
  }, [userId]);

  async function handleApproval(approved, asUser = null) {
    if (!result?.details?.task_id) return;
    setApprovalLoading(true);
    setApprovalMessage('');

    try {
      let authToken = token;
      // If elevating to manager or admin to approve
      if (asUser && asUser !== userId) {
        setUserId(asUser);
        authToken = await fetchTokenForUser(asUser);
      }

      const res = await fetch(`http://127.0.0.1:8000/tasks/${result.details.task_id}/approval`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          approved,
          comments: approved
            ? `Approved via Executive Dashboard by ${asUser || userId}`
            : `Rejected via Executive Dashboard by ${asUser || userId}`,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Approval request failed');
      }

      setApprovalMessage(
        `Task #${result.details.task_id} ${approved ? 'approved & executed with Ollama Qwen' : 'rejected'}.`
      );

      setResult((prev) => ({
        ...prev,
        status: data.status,
        details: {
          ...prev.details,
          ...data,
          approval_status: approved ? 'approved' : 'rejected',
          results: data.results,
          plan: data.plan || prev.details?.plan,
        },
      }));
    } catch (err) {
      setApprovalMessage(`Approval error: ${err.message}`);
    } finally {
      setApprovalLoading(false);
    }
  }

  // Extract artifacts from execution results
  const summaryItem = result?.details?.results?.find((r) => r.details?.summary);
  const emailItem = result?.details?.results?.find((r) => r.details?.email_draft);
  const isPending = result?.details?.approval_status === 'pending';

  return (
    <div className="dashboard-layout">
      {/* ────────────────── TOP EXECUTIVE NAVBAR ────────────────── */}
      <header className="dashboard-navbar">
        <div className="navbar-brand">
          <div className="brand-badge">⚡ Enterprise AI</div>
          <div className="brand-text">
            <h1 className="brand-title">Enterprise Automation Suite</h1>
            <span className="brand-subtitle">Multi-Agent Workflow, Governance &amp; Executive Automation</span>
          </div>
        </div>

        <div className="navbar-right">
          <div className="system-status-indicator">
            <span className="pulse-dot"></span>
            <span className="status-label">Ollama Qwen2.5 Active</span>
          </div>

          <div className="user-profile-widget">
            <div className="user-avatar">👤</div>
            <div className="user-meta">
              <label htmlFor="user-select" className="sr-only">Switch User Profile</label>
              <select
                id="user-select"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="user-select-dropdown"
                title="Switch Active Enterprise User"
              >
                <option value="employee1">employee1 (Employee)</option>
                <option value="employee2">employee2 (Employee)</option>
                <option value="manager">manager (Manager)</option>
                <option value="admin">admin (Administrator)</option>
              </select>
              <span className={`role-pill role-${role}`}>{role.toUpperCase()}</span>
            </div>
          </div>
        </div>
      </header>

      {/* ────────────────── MAIN DASHBOARD GRID ────────────────── */}
      <main className="dashboard-main">
        {tokenError && (
          <div className="dashboard-alert alert-error">
            <span>⚠️ Authentication Notice:</span> {tokenError}
          </div>
        )}

        <div className="dashboard-grid">
          {/* ────── LEFT COLUMN: OPERATIONAL INPUTS ────── */}
          <div className="grid-column-input">
            {/* CARD 1: MEETING NOTES & CONTEXT */}
            <section className="dashboard-card">
              <div className="card-header">
                <div className="card-title-group">
                  <span className="card-number-badge">1</span>
                  <div>
                    <h2 className="card-heading">Meeting Notes &amp; Context</h2>
                    <span className="card-subheading">Dynamic source data processed by Ollama Qwen</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setMeetingNotes(
                      'The team agreed to finish testing by Friday. Ravi will prepare the test report. Priya will fix the login bug. The next review is Monday.'
                    )
                  }
                  className="card-quick-btn"
                  title="Load sample meeting minutes"
                >
                  ⚡ Sample Notes
                </button>
              </div>

              <div className="card-body">
                <textarea
                  value={meetingNotes}
                  onChange={(e) => setMeetingNotes(e.target.value)}
                  rows={4}
                  className="modern-textarea"
                  placeholder="Paste or type meeting notes, decisions, or discussion points here..."
                />
              </div>
            </section>

            {/* CARD 2: VOICE & TASK COMMAND */}
            <section className="dashboard-card">
              <div className="card-header">
                <div className="card-title-group">
                  <span className="card-number-badge">2</span>
                  <div>
                    <h2 className="card-heading">Voice &amp; Task Command</h2>
                    <span className="card-subheading">Speak via microphone or edit prompt</span>
                  </div>
                </div>
              </div>

              <div className="card-body">
                <VoiceRequest
                  token={token}
                  userId={userId}
                  context={{ meeting_notes: meetingNotes }}
                  onResult={(data) => {
                    setResult(data);
                    setApprovalMessage('');
                  }}
                />
              </div>
            </section>
          </div>

          {/* ────── RIGHT COLUMN: WORKFLOW & DELIVERABLES ────── */}
          <div className="grid-column-output">
            <section className="dashboard-card deliverables-master-card">
              <div className="card-header border-bottom">
                <div className="card-title-group">
                  <span className="card-number-badge accent-badge">3</span>
                  <div>
                    <h2 className="card-heading">Workflow Status &amp; Executive Deliverables</h2>
                    <span className="card-subheading">Dynamic outputs generated with Ollama Qwen2.5</span>
                  </div>
                </div>

                {result && (
                  <span
                    className={`kpi-status-badge ${
                      isPending
                        ? 'status-pending'
                        : result.status === 'success'
                        ? 'status-success'
                        : 'status-failed'
                    }`}
                  >
                    {isPending
                      ? '⚠️ HUMAN APPROVAL REQUIRED'
                      : result.status === 'success'
                      ? '✓ EXECUTED SUCCESSFULLY'
                      : 'FAILED'}
                  </span>
                )}
              </div>

              <div className="card-body">
                {!result ? (
                  /* EMPTY STATE */
                  <div className="empty-dashboard-state">
                    <div className="empty-illustration">⚡</div>
                    <h3 className="empty-title">Awaiting Task Execution</h3>
                    <p className="empty-desc">
                      Supply meeting notes on the left, speak or type your request (e.g. <em>“Summarize my meeting notes and prepare a follow-up email”</em>), then click <strong>Run Automation Workflow</strong>.
                    </p>
                    <div className="empty-features-list">
                      <div className="feature-item">
                        <span>🤖</span> Dynamic Ollama Qwen2.5 (7B) Engine
                      </div>
                      <div className="feature-item">
                        <span>🛡️</span> 30/70 Tiered Risk Governance
                      </div>
                      <div className="feature-item">
                        <span>📋</span> Executive MoM &amp; Action Table
                      </div>
                      <div className="feature-item">
                        <span>✉️</span> Outlook Email Preview &amp; Copy
                      </div>
                    </div>
                  </div>
                ) : (
                  /* EXECUTED OR PENDING RESULTS */
                  <div className="results-container">
                    {/* KPI & GOVERNANCE BAR */}
                    <div className="executive-kpi-bar">
                      <div className="kpi-metric-box">
                        <span className="kpi-label">EXECUTION STATUS</span>
                        <span
                          className={`kpi-val ${
                            isPending
                              ? 'val-amber'
                              : result.status === 'success'
                              ? 'val-green'
                              : 'val-red'
                          }`}
                        >
                          {isPending ? 'PENDING APPROVAL' : result.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="kpi-metric-box">
                        <span className="kpi-label">RISK ASSESSMENT</span>
                        <span
                          className={`kpi-val ${
                            result.details?.risk_score > 70
                              ? 'val-red'
                              : result.details?.risk_score > 30
                              ? 'val-amber'
                              : 'val-blue'
                          }`}
                        >
                          {result.details?.risk_score ?? '0'} / 100 (
                          {result.details?.risk_score > 70
                            ? 'High Risk'
                            : result.details?.risk_score > 30
                            ? 'Medium Risk'
                            : 'Low Risk'}
                          )
                        </span>
                      </div>
                      <div className="kpi-metric-box">
                        <span className="kpi-label">GOVERNANCE TIER</span>
                        <span
                          className={`kpi-val ${
                            isPending ? 'val-amber' : 'val-green'
                          }`}
                        >
                          {isPending
                            ? `⚠️ ${result.details?.required_role?.toUpperCase()} REQUIRED`
                            : result.details?.approval_status === 'auto_approved'
                            ? '🛡️ Auto-Approved'
                            : '✓ Human Approved'}
                        </span>
                      </div>
                      <div className="kpi-metric-box">
                        <span className="kpi-label">REFERENCE TASK ID</span>
                        <span className="kpi-val val-purple">
                          #{result.details?.task_id || '34'}
                        </span>
                      </div>
                    </div>

                    {/* HUMAN APPROVAL CARD (WHEN RISK > 30) */}
                    {isPending && (
                      <div className="executive-approval-card">
                        <div className="approval-text-side">
                          <h4>⚠️ Human Governance Authorization Required</h4>
                          <p>
                            {result.details?.message ||
                              'This request involves elevated risk operations and requires supervisory authorization.'}
                          </p>
                          <span className="approval-auth-note">
                            Role requirement: <strong>{result.details?.required_role?.toUpperCase()}</strong> | Active profile: <strong>{role.toUpperCase()}</strong>
                          </span>
                        </div>

                        <div className="approval-actions-side">
                          {approvalLoading ? (
                            <div className="btn-spinner-content" style={{ color: '#92400e', fontWeight: 600 }}>
                              <span className="spinner-ring" style={{ borderColor: '#92400e', borderTopColor: 'transparent' }}></span>
                              Executing with Ollama Qwen…
                            </div>
                          ) : role === 'admin' || (role === 'manager' && result.details?.required_role !== 'admin') ? (
                            <>
                              <button
                                type="button"
                                onClick={() => handleApproval(true)}
                                className="btn-governance-approve"
                              >
                                ✓ Authorize &amp; Execute (as {role.toUpperCase()})
                              </button>
                              <button
                                type="button"
                                onClick={() => handleApproval(false)}
                                className="btn-governance-reject"
                              >
                                ✕ Reject
                              </button>
                            </>
                          ) : (
                            <>
                              {result.details?.required_role !== 'admin' && (
                                <button
                                  type="button"
                                  onClick={() => handleApproval(true, 'manager')}
                                  className="btn-governance-approve"
                                  title="Elevate to Manager and approve"
                                >
                                  👔 Authorize as Manager &amp; Execute
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => handleApproval(true, 'admin')}
                                className="btn-governance-approve"
                                title="Elevate to Administrator and approve"
                              >
                                🛡️ Authorize as Admin &amp; Execute
                              </button>
                              <button
                                type="button"
                                onClick={() => handleApproval(false)}
                                className="btn-governance-reject"
                              >
                                ✕ Reject
                              </button>
                            </>
                          )}
                        </div>

                        {approvalMessage && (
                          <p className="approval-note" style={{ width: '100%', marginTop: 8 }}>
                            {approvalMessage}
                          </p>
                        )}
                      </div>
                    )}

                    {/* AUTOMATED WORKFLOW STEPPER */}
                    {result.details?.plan?.steps && (
                      <div className="workflow-stepper-box">
                        <h3 className="section-title-sm">
                          ⚡ Multi-Agent Execution Pipeline{' '}
                          {isPending && <span className="stepper-pending-tag">(Awaiting Approval)</span>}
                        </h3>
                        <div className="stepper-track">
                          {result.details.plan.steps.map((s, idx) => (
                            <div
                              key={s.step_id}
                              className={`stepper-node ${isPending ? 'pending' : 'completed'}`}
                            >
                              <div className="node-icon">{isPending ? '⏳' : '✓'}</div>
                              <div className="node-content">
                                <span className="node-step">STEP {s.step_id}</span>
                                <span className="node-title">{s.objective}</span>
                                <span className="node-agent">
                                  {s.agent.toUpperCase()} AGENT &bull; {s.action}
                                </span>
                              </div>
                              {idx < result.details.plan.steps.length - 1 && (
                                <div className="stepper-connector"></div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* DELIVERABLES VIEW TABS (WHEN EXECUTED) */}
                    {(summaryItem || emailItem) && (
                      <div className="deliverables-tab-nav">
                        <button
                          type="button"
                          className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`}
                          onClick={() => setActiveTab('all')}
                        >
                          📂 All Deliverables
                        </button>
                        {summaryItem && (
                          <button
                            type="button"
                            className={`tab-btn ${activeTab === 'mom' ? 'active' : ''}`}
                            onClick={() => setActiveTab('mom')}
                          >
                            📋 Minutes of Meeting
                          </button>
                        )}
                        {emailItem && (
                          <button
                            type="button"
                            className={`tab-btn ${activeTab === 'email' ? 'active' : ''}`}
                            onClick={() => setActiveTab('email')}
                          >
                            ✉️ Follow-Up Email
                          </button>
                        )}
                        <button
                          type="button"
                          className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
                          onClick={() => setActiveTab('audit')}
                        >
                          🔍 Audit Trail
                        </button>
                      </div>
                    )}

                    {/* DELIVERABLES DISPLAY AREA */}
                    <div className="deliverables-content-canvas">
                      {/* 1. MINUTES OF MEETING */}
                      {summaryItem && (activeTab === 'all' || activeTab === 'mom') && (
                        <div className="deliverable-block">
                          <MeetingSummaryCard summaryText={summaryItem.details.summary} />
                        </div>
                      )}

                      {/* 2. EMAIL DRAFT */}
                      {emailItem && (activeTab === 'all' || activeTab === 'email') && (
                        <div className="deliverable-block">
                          <EmailDraftCard
                            emailDraft={emailItem.details.email_draft}
                            senderId={userId || 'employee1'}
                          />
                        </div>
                      )}

                      {/* 3. AUDIT TRAIL TAB */}
                      {activeTab === 'audit' && (
                        <div className="audit-trail-panel">
                          <h4 className="audit-panel-title">🛡️ Security &amp; Execution Audit Trail</h4>
                          <table className="audit-table">
                            <thead>
                              <tr>
                                <th>Step</th>
                                <th>Agent</th>
                                <th>Action</th>
                                <th>Execution Status</th>
                                <th>Message</th>
                              </tr>
                            </thead>
                            <tbody>
                              {result.details?.results?.map((item) => (
                                <tr key={item.step_id}>
                                  <td>Step {item.step_id}</td>
                                  <td><strong>{item.agent}</strong></td>
                                  <td><code>{item.action}</code></td>
                                  <td>
                                    <span className={`tag-${item.status}`}>{item.status.toUpperCase()}</span>
                                  </td>
                                  <td>{item.message || 'Completed successfully'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
