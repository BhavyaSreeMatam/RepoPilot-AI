import { uploadRepo, scanRepo, indexRepo, askAgent,generateSummary,debugIssue} from "./api";
import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

function App() {
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

  useEffect(() => {
  setQuestion("");
}, [mode]);

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
      setLoadingAction(true);
      setError("");

      const data = await uploadRepo(selectedFile);


      setUploadResult(data);
      setRepoId(data.repo_id);

      setIndexResult(null);
      setAnswer(null);
      setQuestion("");
      setMode("ask");
      setActiveSection("repositories");
    } catch (err) {
      console.error("Full upload error: " + err);
      setError(err.message || string(err));
    } finally {
      setLoadingAction("");
    }
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
    } catch (err) {
      console.error("INDEX ERROR:", err);
      setError(err.message || String(err));
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

            <div className="status-pill">Backend: Local</div>
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

              {uploadResult ? (
                <div className="repo-empty">
                  <strong>Repository uploaded successfully</strong>

                  <span>
                    Repo ID: {uploadResult.repo_id}
                  </span>

                  <span>
                    Total files found: {uploadResult.total_files_found}
                  </span>

                  <span>
                    Code files found: {uploadResult.code_files_found}
                  </span>

                  <span>
                    Ignored files: {uploadResult.ignored_files}
                  </span>

                   <button
                      className="primary-button"
                      onClick={handleIndex}
                      disabled={loadingAction !== "" || !repoId}
                    >
                      {loadingAction === "index" ? "Indexing..." : "Index Repository"}
                    </button>

                    {indexResult && (
                      <>
                        <strong>Index created successfully</strong>

                        <span>
                          {indexResult.message}
                        </span>

                        <span>
                          Files used for indexing: {indexResult.total_files_used}
                        </span>

                        <span>
                          Chunks indexed: {indexResult.indexed_chunks}
                        </span>
                      </>
                    )}
                </div>
              ) : (
                <div className="repo-empty">
                  <strong>No repositories loaded</strong>
                  <span>
                    Upload a ZIP repository to begin.
                  </span>
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
                  </h3>

                  <p>
                    {mode === "ask" &&
                      "Ask architecture, security, or documentation questions."}
                    {mode === "onboarding" &&
                      "Generate a structured developer onboarding summary."}
                    {mode === "debug" &&
                      "Describe an error or failure and get debugging guidance."}
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
              </div>

              <textarea
                className="question-input"
                rows="7"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={placeholderText[mode]}
              />

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

                <button
                  className="secondary-button"
                  onClick={() => setQuestion("")}
                >
                  Clear
                </button>
              </div>

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
          </section>

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