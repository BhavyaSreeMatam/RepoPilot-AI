const API_BASE_URL = "http://127.0.0.1:8000";

async function handleResponse(response, fallbackMessage) {
  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(
      `${fallbackMessage}. Status: ${response.status}. Response: ${responseText}`
    );
  }

  try {
    return JSON.parse(responseText);
  } catch {
    throw new Error("Backend returned a response that was not valid JSON.");
  }
}

export async function uploadRepo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/repos/upload`, {
    method: "POST",
    body: formData,
  });

  return handleResponse(response, "Failed to upload repository");
}

export async function scanRepo(repoId) {
  const response = await fetch(`${API_BASE_URL}/repos/${repoId}/scan`, {
    method: "GET",
  });

  return handleResponse(response, "Failed to scan repository");
}

export async function indexRepo(repoId) {
  const response = await fetch(`${API_BASE_URL}/repos/${repoId}/index`, {
    method: "POST",
  });

  return handleResponse(response, "Failed to index repository");
}

export async function askAgent(repoId, question) {
  const response = await fetch(`${API_BASE_URL}/agent/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repo_id: repoId,
      question: question,
    }),
  });

  return handleResponse(response, "Failed to get AI answer");
}

export async function generateSummary(repoId) {
  const response = await fetch(`${API_BASE_URL}/agent/summarize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repo_id: repoId,
    }),
  });

  return handleResponse(response, "Failed to generate onboarding summary");
}

export async function debugIssue(repoId, issue) {
  const response = await fetch(`${API_BASE_URL}/agent/debug`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      repo_id: repoId,
      error_message: issue,
    }),
  });

  return handleResponse(response, "Failed to debug issue");
}