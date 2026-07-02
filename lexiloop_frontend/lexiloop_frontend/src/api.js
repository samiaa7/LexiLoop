const BASE = "/api";

function getToken() {
  return localStorage.getItem("lexiloop_token");
}

async function request(path, { method = "GET", body, auth = true, isForm = false } = {}) {
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  signup: (payload) => request("/auth/signup", { method: "POST", body: payload, auth: false }),
  login: (payload) => request("/auth/login", { method: "POST", body: payload, auth: false }),

  listChildren: () => request("/children"),
  createChild: (payload) => request("/children", { method: "POST", body: payload }),
  getChild: (id) => request(`/children/${id}`),

  detectHandwriting: (childId, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/detect/${childId}`, { method: "POST", body: form, isForm: true });
  },

  simplify: (text) => request("/simplify", { method: "POST", body: { text } }),
  readability: (text) => request("/simplify/readability", { method: "POST", body: { text } }),

  chat: (childId, message) =>
    request("/chat", { method: "POST", body: { child_id: childId, message } }),

  generateExercise: (childId) =>
    request("/exercises", { method: "POST", body: { child_id: childId } }),
};

export function saveToken(token) {
  localStorage.setItem("lexiloop_token", token);
}

export function clearToken() {
  localStorage.removeItem("lexiloop_token");
}

export function isLoggedIn() {
  return Boolean(getToken());
}
