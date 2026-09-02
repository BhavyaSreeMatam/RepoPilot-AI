import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { Amplify } from "aws-amplify";

import {
  Authenticator,
  useAuthenticator,
} from "@aws-amplify/ui-react";

import "@aws-amplify/ui-react/styles.css";

import "./index.css";
import App from "./App.jsx";


Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId:
        import.meta.env
          .VITE_COGNITO_USER_POOL_ID,

      userPoolClientId:
        import.meta.env
          .VITE_COGNITO_USER_POOL_CLIENT_ID,

      loginWith: {
        email: true,
      },
    },
  },
});


function RepoPilotRoot() {
  const {
    authStatus,
    user,
    signOut,
  } = useAuthenticator((context) => [
    context.authStatus,
    context.user,
  ]);

  if (authStatus === "authenticated") {
    return (
      <App
        signOut={signOut}
        user={user}
      />
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-layout">

        <section className="auth-showcase">
          <div className="auth-brand">
            <div className="auth-brand-icon">
              <span>&lt; / &gt;</span>
            </div>

            <div>
              <h1>RepoPilot-AI</h1>
              <p>AI Engineering Copilot</p>
            </div>
          </div>

          <div className="auth-showcase-content">
            <p className="auth-eyebrow">
              CODEBASE UNDERSTANDING PLATFORM
            </p>

            <h2>
              Understand any codebase.
              <br />
              Faster.
            </h2>

            <p className="auth-description">
              Upload repositories and use
              specialized AI agents for
              architecture analysis, onboarding,
              debugging, and security review.
            </p>

            <div className="auth-features">
              <div>
                <strong>Multi-Agent AI</strong>
                <span>
                  Specialized engineering agents
                </span>
              </div>

              <div>
                <strong>Source Grounded</strong>
                <span>
                  Answers backed by repository code
                </span>
              </div>

              <div>
                <strong>Private Workspaces</strong>
                <span>
                  Repositories isolated per user
                </span>
              </div>

              <div>
                <strong>Security Review</strong>
                <span>
                  Deterministic + AI analysis
                </span>
              </div>
            </div>
          </div>

          <div className="auth-showcase-footer">
            Multi-agent RAG engineering platform
          </div>
        </section>


        <section className="auth-form-side">
          <div className="auth-form-heading">
            <p className="auth-eyebrow">
              REPOPILOT WORKSPACE
            </p>

            <h2>Welcome back</h2>

            <p>
              Sign in or create an account to
              access your repository workspace.
            </p>
          </div>

          <div className="authenticator-container">
            <Authenticator
              loginMechanisms={["email"]}
            />
          </div>
        </section>

      </div>
    </div>
  );
}


createRoot(
  document.getElementById("root")
).render(
  <StrictMode>
    <Authenticator.Provider>
      <RepoPilotRoot />
    </Authenticator.Provider>
  </StrictMode>
);