import { fetchAuthSession } from "aws-amplify/auth";


const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


async function getAuthorizationHeaders(
  extraHeaders = {}
) {
  const session = await fetchAuthSession();

  const accessToken =
    session.tokens?.accessToken?.toString();

  if (!accessToken) {
    throw new Error(
      "Authentication session not found. Please sign in again."
    );
  }

  return {
    ...extraHeaders,
    Authorization: `Bearer ${accessToken}`,
  };
}


async function handleResponse(
  response,
  fallbackMessage
) {
  const responseText = await response.text();

  if (!response.ok) {
    let detail = responseText;

    try {
      const parsed = JSON.parse(responseText);

      if (parsed.detail) {
        detail = parsed.detail;
      }
    } catch {
      // Keep the raw response text when it is not JSON.
    }

    if (response.status === 401) {
      throw new Error(
        "Your authentication session is invalid or expired. Please sign in again."
      );
    }

    if (response.status === 403) {
      throw new Error(
        "You do not have permission to access this repository."
      );
    }

    if (response.status === 404) {
      throw new Error(
        detail || "Repository not found."
      );
    }

    throw new Error(
      `${fallbackMessage}. Status: ${response.status}. Response: ${detail}`
    );
  }

  try {
    return JSON.parse(responseText);
  } catch {
    throw new Error(
      "Backend returned a response that was not valid JSON."
    );
  }
}


export async function uploadRepo(file) {
  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  const headers =
    await getAuthorizationHeaders();

  const response = await fetch(
    `${API_BASE_URL}/repos/upload`,
    {
      method: "POST",
      headers,
      body: formData,
    }
  );

  return handleResponse(
    response,
    "Failed to upload repository"
  );
}


export async function scanRepo(repoId) {
  const headers =
    await getAuthorizationHeaders();

  const response = await fetch(
    `${API_BASE_URL}/repos/${repoId}/scan`,
    {
      method: "GET",
      headers,
    }
  );

  return handleResponse(
    response,
    "Failed to scan repository"
  );
}


export async function indexRepo(repoId) {
  const headers =
    await getAuthorizationHeaders();

  const response = await fetch(
    `${API_BASE_URL}/repos/${repoId}/index`,
    {
      method: "POST",
      headers,
    }
  );

  return handleResponse(
    response,
    "Failed to index repository"
  );
}


export async function askAgent(
  repoId,
  question
) {
  const headers =
    await getAuthorizationHeaders({
      "Content-Type": "application/json",
    });

  const response = await fetch(
    `${API_BASE_URL}/agent/ask`,
    {
      method: "POST",
      headers,

      body: JSON.stringify({
        repo_id: repoId,
        question,
      }),
    }
  );

  return handleResponse(
    response,
    "Failed to get AI answer"
  );
}


export async function generateSummary(
  repoId
) {
  const headers =
    await getAuthorizationHeaders({
      "Content-Type": "application/json",
    });

  const response = await fetch(
    `${API_BASE_URL}/agent/summarize`,
    {
      method: "POST",
      headers,

      body: JSON.stringify({
        repo_id: repoId,
      }),
    }
  );

  return handleResponse(
    response,
    "Failed to generate onboarding summary"
  );
}


export async function debugIssue(
  repoId,
  issue
) {
  const headers =
    await getAuthorizationHeaders({
      "Content-Type": "application/json",
    });

  const response = await fetch(
    `${API_BASE_URL}/agent/debug`,
    {
      method: "POST",
      headers,

      body: JSON.stringify({
        repo_id: repoId,
        error_message: issue,
      }),
    }
  );

  return handleResponse(
    response,
    "Failed to debug issue"
  );
}


export async function securityReview(
  repoId
) {
  const headers =
    await getAuthorizationHeaders({
      "Content-Type": "application/json",
    });

  const response = await fetch(
    `${API_BASE_URL}/agent/ask`,
    {
      method: "POST",
      headers,

      body: JSON.stringify({
        repo_id: repoId,

        question:
          "Perform a security review of this repository. Check for unsafe deserialization, command execution, secrets, insecure configuration, cryptographic weaknesses, unsafe file handling, CI/CD risks, Docker risks, and other security issues.",
      }),
    }
  );

  return handleResponse(
    response,
    "Failed to run security review"
  );
}


export async function listRepos() {
  const headers =
    await getAuthorizationHeaders();

  const response = await fetch(
    `${API_BASE_URL}/repos`,
    {
      method: "GET",
      headers,
    }
  );

  return handleResponse(
    response,
    "Failed to load repositories"
  );
}

export async function deleteRepo(repoId) {
  const headers =
    await getAuthorizationHeaders();

  const response = await fetch(
    `${API_BASE_URL}/repos/${repoId}`,
    {
      method: "DELETE",
      headers,
    }
  );

  return handleResponse(
    response,
    "Failed to remove repository"
  );
}