import { uploadRepo, scanRepo, indexRepo, askAgent,generateSummary,debugIssue,securityReview,listRepos,deleteRepo,} from "./api";
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

function App({signOut,user}) {
    const signedInUser =
    user?.signInDetails?.loginId ||
    user?.username ||
    "Signed in";
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileName, setSelectedFileName] = useState("");

  const [repoId, setRepoId] = useState("");
  const [uploadResult, setUploadResult] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [indexResult, setIndexResult] = useState(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);

  const [loadingAction, setLoadingAction] = useState("");
  const [error, setError] = useState("");

  const [activeSection, setActiveSection] = useState("repositories");
  const [mode, setMode] = useState("ask");

  const [repositories, setRepositories] = useState([]);

  useEffect(() => {
  setQuestion("");
}, [mode]);

useEffect(() => {
  async function loadRepositories() {
    try {
      const data = await listRepos();
      setRepositories(data.repositories || []);
    } catch (err) {
      console.error("LOAD REPOSITORIES ERROR:", err);
    }
  }

  loadRepositories();
}, []);

  const placeholderText = {
    ask: "Example: Explain how this repository is organized and how the main components interact.",
    onboarding:
      "Click Generate Summary to create a developer onboarding summary for the selected repository.",
    debug:
      "Example: Package repository signing fails during buildmaster repository creation.",
  };
  async function handleUpload() {
    
    if (!selectedFile) {
      setError("Please select a ZIP file first.");
      return;
    }


    try {
      setLoadingAction("upload");
      setError("");

      const data = await uploadRepo(selectedFile);

      setUploadResult(data);
      setRepoId(data.repo_id);

      const repositoriesData = await listRepos();

      setRepositories(
        repositoriesData.repositories || []
      );

      setIndexResult(null);
      setAnswer(null);
      setQuestion("");
      setMode("ask");
      setActiveSection("repositories");
    } catch (err) {
      console.error("Full upload error: " + err);
      setError(err.message || String(err));
    } finally {
      setLoadingAction("");
    }
  }

  function handleSelectRepository(repository) {
  setRepoId(repository.repo_id);

  // This repository came from the persisted backend list,
  // not from a fresh upload in this browser session.
  setUploadResult(null);

  // GET /repos tells us whether this repository is indexed.
  // This allows Ask / Onboarding / Debug / Security buttons to work
  // for repositories restored after a restart.
  if (repository.indexed) {
    setIndexResult({
      message: "Existing repository index is available.",
      existing: true,
    });
  } else {
    setIndexResult(null);
  }

  setAnswer(null);
  setQuestion("");
  setError("");
  setActiveSection("repositories");
}

  async function handleIndex() {
    if (!repoId) {
      setError("Please upload a repository first.");
      return;
    }

    try {
      setLoadingAction("index");
      setError("");

      const data = await indexRepo(repoId);

      setIndexResult(data);



      setRepositories((currentRepositories) =>
      currentRepositories.map((repository) =>
        repository.repo_id === repoId
          ? {
              ...repository,
              indexed: true,
            }
          : repository
      )
    );

    } catch (err) {
      console.error("INDEX ERROR:", err);
      setError(err.message || String(err));
    } finally {
      setLoadingAction("");
      }
    }


    async function handleDeleteRepository() {
  if (!repoId) {
    setError("Please select a repository first.");
    return;
  }

  const selectedRepository =
    repositories.find(
      (repository) =>
        repository.repo_id === repoId
    );

  const repositoryName =
    selectedRepository?.repo_name ||
    selectedRepository?.original_filename ||
    "this repository";

  const confirmed = window.confirm(
    `Remove "${repositoryName}"?\n\nThis will permanently delete the uploaded repository and its vector index from RepoPilot.`
  );

  if (!confirmed) {
    return;
  }

  try {
    setLoadingAction("delete");
    setError("");

    await deleteRepo(repoId);

    setRepositories(
      (currentRepositories) =>
        currentRepositories.filter(
          (repository) =>
            repository.repo_id !== repoId
        )
    );

    setRepoId("");
    setUploadResult(null);
    setScanResult(null);
    setIndexResult(null);
    setAnswer(null);
    setQuestion("");
    setMode("ask");
    setActiveSection("repositories");
    setSelectedFile(null);
    setSelectedFileName("");
  } catch (err) {
    console.error(
      "DELETE REPOSITORY ERROR:",
      err
    );

    setError(
      err.message || String(err)
    );
  } finally {
    setLoadingAction("");
  }
}


  async function handleAsk() {
    if (!repoId) {
      setError("Please upload a repository first.");
      return;
    }

    if (!indexResult) {
      setError("Please index the repository before asking questions.");
      return;
    }

    if (!question.trim()) {
      setError("Please enter a question.");
      return;
    }

    try {
      setLoadingAction("ask");
      setError("");

      const data = await askAgent(repoId, question);

      setAnswer(data);
    } catch (err) {
      console.error("ASK ERROR:", err);
    setError(err.message || String(err));
  } finally {
    setLoadingAction("");
    }
  }

  
  async function handleSummary() {
  if (!repoId) {
    setError("Please upload a repository first.");
    return;
  }

  if (!indexResult) {
    setError("Please index the repository before generating a summary.");
    return;
  }

  try {
    setLoadingAction("summary");
    setError("");

    const data = await generateSummary(repoId);

    setAnswer(data);
    setMode("onboarding");
  } catch (err) {
    console.error("SUMMARY ERROR:", err);
    setError(err.message || String(err));
  } finally {
    setLoadingAction("");
  }
}


  async function handleDebug() {
  if (!repoId) {
      setError("Please upload a repository first.");
      return;
    }

    if (!indexResult) {
      setError("Please index the repository before debugging an issue.");
      return;
    }

    if (!question.trim()) {
      setError("Please describe the issue you want to debug.");
      return;
    }

    try {
      setLoadingAction("debug");
      setError("");

      const data = await debugIssue(repoId, question);

      setAnswer(data);
      setMode("debug");
    } catch (err) {
      console.error("DEBUG ERROR:", err);
      setError(err.message || String(err));
    } finally {
      setLoadingAction("");
    }
  }

  async function handleSecurityReview() {
  if (!repoId) {
    setError("Please upload a repository first.");
    return;
  }

  if (!indexResult) {
    setError("Please index the repository before running a security review.");
    return;
  }

  try {
    setLoadingAction("security");
    setError("");

    const data = await securityReview(repoId);

    setAnswer(data);
    setMode("security");
    setActiveSection("security");
  } catch (err) {
    console.error("SECURITY REVIEW ERROR:", err);
    setError(err.message || String(err));
  } finally {
    setLoadingAction("");
  }
}


  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"> 
            <span>&lt; / &gt;</span>
            </div>

          <div className="brand-text">
            <h1>RepoPilot-AI</h1>
            <p>AI Engineering Copilot</p>
          </div>
        </div>

        <nav className="nav">
  <button
    className={`nav-item ${activeSection === "repositories" ? "active" : ""}`}
    onClick={() => setActiveSection("repositories")}
  >
    Repositories
  </button>

  <button
    className={`nav-item ${activeSection === "ask" ? "active" : ""}`}
    onClick={() => {
      setActiveSection("ask");
      setMode("ask");
      setQuestion("");
    }}
  >
    Ask RepoPilot
  </button>

  <button
    className={`nav-item ${activeSection === "onboarding" ? "active" : ""}`}
    onClick={() => {
      setActiveSection("onboarding");
      setMode("onboarding");
      setQuestion("");
    }}
  >
    Onboarding
  </button>

  <button
    className={`nav-item ${activeSection === "debug" ? "active" : ""}`}
    onClick={() => {
      setActiveSection("debug");
      setMode("debug");
      setQuestion("");
    }}
  >
    Debug Assistant
  </button>

  <button
    className={`nav-item ${activeSection === "security" ? "active" : ""}`}
    onClick={() => {
      setActiveSection("security");
      setMode("security");
      setQuestion("");
    }}
  >
    Security Review
  </button>



</nav>

        <div className="sidebar-footer">
          <p>Multi-agent RAG system</p>
          <span>Local Demo</span>
        </div>
      </aside>

      <main className="main">
        <div className="page-shell">
          <header className="hero">
            <div>
              <p className="eyebrow">Codebase Understanding Platform</p>
              <h2>Repository Workspace</h2>
              <p>
                Upload a repository, index the codebase, ask engineering
                questions, generate onboarding summaries, and debug issues with
                specialized AI agents.
              </p>
            </div>

            <div
              style={{
                display: "flex",
                gap: "12px",
                alignItems: "center",
                flexWrap: "wrap",
                justifyContent: "flex-end",
              }}
            >
              <div className="status-pill">
                Signed in: {signedInUser}
              </div>

              <button
                type="button"
                className="secondary-button"
                onClick={signOut}
              >
                Sign Out
              </button>
            </div>
          </header>

          {error && (
            <div className="error-banner">
              <strong>Error</strong>
              <span>{error}</span>
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}

          <section className="top-grid">
            <div className="card upload-card">
              <div className="card-header">
                <div>
                  <h3>Upload Repository</h3>
                  <p>Upload a ZIP file containing a codebase.</p>
                </div>
              </div>

              <label className="upload-box">
                <input
                  type="file"
                  accept=".zip"
                  hidden
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    setSelectedFile(file || null);
                    setSelectedFileName(file ? file.name : "");
                  }}
                />

                <span>Choose ZIP file</span>
                <small>{selectedFileName || "No file selected yet"}</small>
              </label>

              <button
                className="primary-button"
                onClick={handleUpload}
                disabled={loadingAction !== ""}
              >
                {loadingAction === "upload" ? "Uploading..." : "Upload Repository"}
              </button>
            </div>

            <div className="card repository-card">
              <div className="card-header">
                <div>
                  <h3>Repositories</h3>
                  <p>Select an uploaded repository before asking questions.</p>
                </div>
              </div>

              {repositories.length > 0 ? (
                <div className="repository-list">
                  {repositories.map((repository) => (
                    <button
                      key={repository.repo_id}
                      type="button"
                      className={`repository-list-item ${
                        repoId === repository.repo_id ? "selected" : ""
                      }`}
                      onClick={() => handleSelectRepository(repository)}
                    >
                      <div className="repository-list-main">
                        <strong>
                          {repository.repo_name ||
                            repository.original_filename ||
                            "Repository"}
                        </strong>

                        <span>{repository.original_filename}</span>
                      </div>

                      <div className="repository-list-meta">
                        <span className="repository-id">
                          {repository.repo_id}
                        </span>

                        <span
                          className={`repository-index-status ${
                            repository.indexed ? "indexed" : "not-indexed"
                          }`}
                        >
                          {repository.indexed ? "Indexed" : "Not Indexed"}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="repo-empty">
                  <strong>No repositories loaded</strong>
                  <span>Upload a ZIP repository to begin.</span>
                </div>
              )}

              {repoId && (
                <div className="selected-repository-panel">
                  <strong>Selected Repository</strong>

                  <span>Repo ID: {repoId}</span>

                  {uploadResult && (
                    <>
                      <span>
                        Total files found: {uploadResult.total_files_found}
                      </span>

                      <span>
                        Code files found: {uploadResult.code_files_found}
                      </span>

                      <span>
                        Ignored files: {uploadResult.ignored_files}
                      </span>
                    </>
                  )}

                  {indexResult?.existing ? (
                    <div className="existing-index-message">
                      Existing repository index is available.
                    </div>
                  ) : (
                    <button
                      className="primary-button"
                      onClick={handleIndex}
                      disabled={loadingAction !== "" || !repoId}
                    >
                      {loadingAction === "index"
                        ? "Indexing..."
                        : indexResult
                        ? "Re-index Repository"
                        : "Index Repository"}
                    </button>
                  )}

                  {indexResult && !indexResult.existing && (
                    <div className="index-result-summary">
                      <strong>Index created successfully</strong>

                      <span>{indexResult.message}</span>

                      {indexResult.total_files_used !== undefined && (
                        <span>
                          Files used for indexing: {indexResult.total_files_used}
                        </span>
                      )}

                      {indexResult.indexed_chunks !== undefined && (
                        <span>
                          Chunks indexed: {indexResult.indexed_chunks}
                        </span>
                      )}
                    </div>
                  )}
                  <button
                    type="button"
                    className="danger-button"
                    onClick={handleDeleteRepository}
                    disabled={loadingAction !== ""}
                  >
                    {loadingAction === "delete"
                      ? "Removing..."
                      : "Remove Repository"}
                  </button>
                </div>
              )}
            </div>
          </section>

          <section className="ask-layout">
            <div className="card ask-card">
              <div className="card-header">
                <div>
                  <h3>
                    {mode === "ask" && "Ask RepoPilot"}
                    {mode === "onboarding" && "Onboarding Summary"}
                    {mode === "debug" && "Debug Assistant"}
                    {mode === "security" && "Security Review"}
                  </h3>

                  <p>
                    {mode === "ask" &&
                      "Ask architecture, security, or documentation questions."}
                    {mode === "onboarding" &&
                      "Generate a structured developer onboarding summary."}
                    {mode === "debug" &&
                      "Describe an error or failure and get debugging guidance."}
                    {mode === "security" &&
                      "Run a repository-wide security scan and AI-assisted security analysis."}
                  </p>
                </div>
              </div>
            </div>
              <div className="mode-tabs">
                <button
                  className={mode === "ask" ? "mode-tab active" : "mode-tab"}
                  onClick={() => setMode("ask")}
                >
                  Ask
                </button>

                <button
                  className={mode === "onboarding" ? "mode-tab active" : "mode-tab"}
                  onClick={() => setMode("onboarding")}
                >
                  Onboarding
                </button>

                <button
                  className={mode === "debug" ? "mode-tab active" : "mode-tab"}
                  onClick={() => setMode("debug")}
                >
                  Debug
                </button>

                <button
                  className={mode === "security" ? "mode-tab active" : "mode-tab"}
                  onClick={() => {
                    setMode("security");
                    setActiveSection("security");
                    setQuestion("");
                  }}
                >
                  Security
                </button>
              </div>

              {mode !== "security" ? (
                <textarea
                  className="question-input"
                  rows="7"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder={placeholderText[mode]}
                />
              ) : (
                <div className="security-intro">
                  <strong>Repository Security Review</strong>

                  <p>
                    RepoPilot will scan the repository for security-sensitive patterns
                    and combine those findings with retrieved code context for analysis
                    by the MCP Security Agent.
                  </p>

                  <div className="security-check-list">
                    <span>Unsafe deserialization</span>
                    <span>Secrets and credentials</span>
                    <span>Command execution</span>
                    <span>Insecure configuration</span>
                    <span>Cryptographic weaknesses</span>
                    <span>Docker and CI/CD risks</span>
                  </div>
                </div>
              )}

              <div className="button-row">
                {mode === "ask" && (
                  <button
                    className="primary-button"
                    onClick={handleAsk}
                    disabled={loadingAction !== "" || !repoId || !indexResult}
                  >
                    {loadingAction === "ask" ? "Thinking..." : "Ask Question"}
                  </button>
                )}

                {mode === "onboarding" && (
                  <button
                    className="primary-button"
                    onClick={handleSummary}
                    disabled={loadingAction !== "" || !repoId || !indexResult}
                  >
                    {loadingAction === "summary" ? "Generating..." : "Generate Summary"}
                  </button>
                )}

                {mode === "debug" && (
                  <button
                    className="primary-button"
                    onClick={handleDebug}
                    disabled={loadingAction !== "" || !repoId || !indexResult}
                  >
                    {loadingAction === "debug" ? "Debugging..." : "Debug Issue"}
                  </button>
                )}

                {mode === "security" && (
                  <button
                    className="primary-button"
                    onClick={handleSecurityReview}
                    disabled={loadingAction !== "" || !repoId || !indexResult}
                  >
                    {loadingAction === "security"
                      ? "Scanning Repository..."
                      : "Run Security Review"}
                  </button>
                )}

                {mode !== "security" && (
                  <button
                    className="secondary-button"
                    onClick={() => setQuestion("")}
                  >
                    Clear
                  </button>
                )}
              </div>

            {mode !== "security" && (
              <div className="card answer-card">
              <div className="answer-top">
                <div>
                  <h3>Agent Answer</h3>
                  <p>Responses from the multi-agent backend will appear here.</p>
                </div>

                <span className="route-pill">
                  Route: {answer?.route || "waiting"}
                </span>
              </div>

              {answer ? (
                <div className="answer-preview">
                  <div className="answer-meta-row">
                    <span>
                      Repository: {answer.repo_id}
                    </span>

                    <span>
                      Verified: {answer.verified ? "Yes" : "No"}
                    </span>
                  </div>

                  <h4>
                    {answer.route === "debug" || answer.route === "bug"
                      ? "Issue"
                      : answer.route === "onboarding" || answer.route === "summary"
                      ? "Summary Request"
                      : answer.route === "security"
                      ? "Security Review Request"
                      : "Question"}
                  </h4>

                  <p>
                    {answer.question || answer.error_message || "Generated repository summary"}
                  </p>

                  <h4>
                    {answer.route === "debug" || answer.route === "bug"
                      ? "Debug Guidance"
                      : answer.route === "onboarding" || answer.route === "summary"
                      ? "Onboarding Summary"
                      : answer.route === "security"
                      ? "Security Analysis"
                      : "Answer"}
                  </h4>

                  <div className="answer-text">
                    <ReactMarkdown>
                      {answer.answer || answer.summary || answer.debug_answer || "No answer text returned."}
                    </ReactMarkdown>
                  </div>
                </div>
              ) : (
                <div className="answer-preview">
                  <h4>Ready for a repository question</h4>
                  <p>
                    Upload and index a repository, then ask a question to see the answer here.
                  </p>
                </div>
              )}
            </div>
            )}
          </section>

          {mode === "security" && (
            <section className="security-dashboard">
              <div className="security-dashboard-header">
                <div>
                  <p className="eyebrow">Repository Security</p>
                  <h3>Security Scan Results</h3>
                  <p>
                    Deterministic repository scanning combined with MCP-based
                    AI security analysis.
                  </p>
                </div>

                {answer?.route === "security" && (
                  <span
                    className={`security-status ${
                      answer.verified ? "verified" : "review"
                    }`}
                  >
                    {answer.verified ? "Verified" : "Needs Review"}
                  </span>
                )}
              </div>

              {answer?.route === "security" &&
              answer?.security_scan_summary ? (
                <>
                  <div className="security-stats">
                    <div className="security-stat-card">
                      <span>Files Scanned</span>
                      <strong>
                        {answer.security_scan_summary.files_scanned ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card">
                      <span>Files Skipped</span>
                      <strong>
                        {answer.security_scan_summary.files_skipped ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card">
                      <span>Total Findings</span>
                      <strong>
                        {answer.security_scan_summary.findings_count ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card critical">
                      <span>Critical</span>
                      <strong>
                        {answer.security_scan_summary.severity_counts?.CRITICAL ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card high">
                      <span>High</span>
                      <strong>
                        {answer.security_scan_summary.severity_counts?.HIGH ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card medium">
                      <span>Medium</span>
                      <strong>
                        {answer.security_scan_summary.severity_counts?.MEDIUM ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card low">
                      <span>Low</span>
                      <strong>
                        {answer.security_scan_summary.severity_counts?.LOW ?? 0}
                      </strong>
                    </div>

                    <div className="security-stat-card info">
                      <span>Info</span>
                      <strong>
                        {answer.security_scan_summary.severity_counts?.INFO ?? 0}
                      </strong>
                    </div>
                  </div>

                  <div className="security-findings-card">
                    <div className="security-findings-header">
                      <div>
                        <h3>Security Findings</h3>
                        <p>
                          Potential security-sensitive patterns detected across
                          the repository.
                        </p>
                      </div>
                    </div>

                    {answer.security_findings?.length > 0 ? (
                      <div className="security-findings-list">
                        {answer.security_findings.map((finding, index) => (
                          <div
                            className="security-finding"
                            key={`${finding.rule_id}-${index}`}
                          >
                            <div className="security-finding-top">
                              <span
                                className={`severity-badge severity-${finding.severity?.toLowerCase()}`}
                              >
                                {finding.severity}
                              </span>

                              <span className="rule-id">
                                {finding.rule_id}
                              </span>
                            </div>

                            <h4>
                              {finding.category
                                ?.replaceAll("_", " ")
                                .replace(/\b\w/g, (letter) =>
                                  letter.toUpperCase()
                                )}
                            </h4>

                            <div className="finding-location">
                              <strong>{finding.file_path}</strong>

                              <span>
                                Line {finding.start_line}
                                {finding.end_line &&
                                finding.end_line !== finding.start_line
                                  ? `–${finding.end_line}`
                                  : ""}
                              </span>
                            </div>

                            <p>{finding.message}</p>

                            {finding.evidence && (
                              <pre className="finding-evidence">
                                <code>{finding.evidence}</code>
                              </pre>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="security-empty">
                        <strong>No security findings detected</strong>
                        <span>
                          The scanner did not find any configured security
                          patterns in this repository.
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="security-analysis-card">
                    <h3>AI Security Analysis</h3>

                    <p>
                      Analysis generated by RepoPilot's MCP Security Agent using
                      repository context and deterministic scanner findings.
                    </p>

                    <div className="security-analysis-text">
                      <ReactMarkdown>
                        {answer.answer || "No security analysis returned."}
                      </ReactMarkdown>
                    </div>
                  </div>
                </>
              ) : (
                <div className="security-empty-state">
                  <strong>No security scan has been run yet</strong>

                  <p>
                    Upload and index a repository, then click Run Security Review.
                  </p>
                </div>
              )}
            </section>
          )}

          <section className="insight-grid">
            <div className="card">
              <h3>Sources</h3>
              <p>Retrieved files and line ranges used by the agent.</p>

              <div className="source-list">
                {answer?.sources && answer.sources.length > 0 ? (
                  answer.sources.map((source, index) => (
                    <div className="source-item" key={index}>
                      <div>
                        <strong>{source.file_path}</strong>
                        <span>{source.language || "Unknown language"}</span>
                      </div>

                      <small>
                        Lines {source.start_line}–{source.end_line}
                      </small>
                    </div>
                  ))
                ) : (
                  <div className="source-item">
                    <div>
                      <strong>No sources yet</strong>
                      <span>Ask a question after indexing to see retrieved files.</span>
                    </div>

                    <small>Waiting</small>
                  </div>
                )}
              </div>
            </div>

            <div className="card">
              <h3>Agent Steps</h3>
              <p>The LangGraph execution trace used for this answer.</p>

              <ol className="steps-list">
                {answer?.steps && answer.steps.length > 0 ? (
                  answer.steps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))
                ) : (
                  <li>Ask a question after indexing to see agent steps.</li>
                )}
              </ol>
            </div>

            <div className="card verifier-card">
              <h3>Verifier</h3>
              <p>Grounding validation result from the verifier agent.</p>

              <div className="verified-box">
                {answer ? (
                  <>
                    <strong>
                      {answer.verified ? "Verified answer" : "Needs review"}
                    </strong>

                    <span>
                      {answer.verified
                        ? "The verifier marked this answer as grounded in retrieved code context."
                        : "The verifier could not fully confirm this answer from retrieved context."}
                    </span>

                    {answer.verifier_notes && (
                      <div className="verifier-notes">
                        {answer.verifier_notes}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <strong>Waiting for answer</strong>
                    <span>No verifier result yet.</span>
                  </>
                )}
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;