import React, { useMemo, useState } from "react";

const COGNITO_REGION = "us-east-1";
const COGNITO_CLIENT_ID = "3dppmlrlpd74mnr4alnmfdai15";
const API_BASE_URL =
  "https://y7s2fldy14.execute-api.us-east-1.amazonaws.com/prod";

function pretty(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

function safeJsonParse(s) {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

async function cognitoLogin({ username, password }) {
  const res = await fetch(
    `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target":
          "AWSCognitoIdentityProviderService.InitiateAuth",
      },
      body: JSON.stringify({
        AuthFlow: "USER_PASSWORD_AUTH",
        ClientId: COGNITO_CLIENT_ID,
        AuthParameters: {
          USERNAME: username,
          PASSWORD: password,
        },
      }),
    }
  );

  const data = await res.json();

  if (!res.ok)
    throw new Error(data?.message || "Login failed");

  const token =
    data?.AuthenticationResult?.AccessToken;

  if (!token)
    throw new Error("No AccessToken returned");

  return token;
}

async function callQueryApi({ token, payload }) {
  const res = await fetch(
    `${API_BASE_URL}/query`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }
  );

  const text = await res.text();
  let parsed =
    safeJsonParse(text) ?? { raw: text };

  if (parsed && typeof parsed.body === "string") {
    parsed =
      safeJsonParse(parsed.body) ??
      parsed.body;
  }

  if (!res.ok) {
    throw new Error(
      parsed?.error ||
        parsed?.message ||
        `API error (${res.status})`
    );
  }

  return parsed;
}

/* =============================
   TABLE COMPONENT
============================= */
function ResultsTable({ result }) {
  if (!result) return null;

  const rows =
    result?.data?.rows ||
    result?.rows ||
    [];

  if (!Array.isArray(rows) || rows.length === 0) {
    return (
      <div style={{ marginTop: 20 }}>
        No rows returned.
      </div>
    );
  }

  const columns = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row || {}).forEach((k) =>
        set.add(k)
      );
      return set;
    }, new Set())
  );

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ marginBottom: 8 }}>
        Rows:{" "}
        {result?.data?.row_count ??
          rows.length}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col} style={thStyle}>
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td key={col} style={tdStyle}>
                    {row[col] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* =============================
   MAIN APP
============================= */
export default function App() {
  const [username, setUsername] =
    useState("");
  const [password, setPassword] =
    useState("");
  const [token, setToken] =
    useState("");

  const [input, setInput] =
    useState("");
  const [busy, setBusy] =
    useState(false);
  const [out, setOut] =
    useState(null);
  const [err, setErr] =
    useState("");

  const tokenShort = useMemo(() => {
    if (!token) return "";
    return token.slice(0, 16) + "...";
  }, [token]);

  async function onLogin(e) {
    e.preventDefault();
    setErr("");
    setOut(null);
    setBusy(true);

    try {
      if (!username || !password)
        throw new Error(
          "Enter username and password"
        );

      const t =
        await cognitoLogin({
          username,
          password,
        });

      setToken(t);
    } catch (ex) {
      setErr(ex.message || String(ex));
    } finally {
      setBusy(false);
    }
  }

  async function onRun(e) {
    e.preventDefault();
    setErr("");
    setOut(null);

    if (!token)
      return setErr("Login first.");

    if (!input.trim())
      return setErr(
        "Enter SQL or natural language question."
      );

    const trimmed = input.trim();
    const isSQL =
      /^(SELECT|WITH)\b/i.test(trimmed);

    const payload = isSQL
      ? { sql: trimmed }
      : { question: trimmed };

    setBusy(true);

    try {
      const data =
        await callQueryApi({
          token,
          payload,
        });

      setOut(data);
    } catch (ex) {
      setErr(ex.message || String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={pageStyle}>
      <div
        style={{
          maxWidth: 900,
          margin: "0 auto",
        }}
      >
        <h1>WorldBank Query UI</h1>

        {/* LOGIN */}
        <div style={cardStyle}>
          <h2>Login</h2>
          <form onSubmit={onLogin}>
            <input
              placeholder="Username"
              value={username}
              onChange={(e) =>
                setUsername(e.target.value)
              }
              style={inputStyle}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) =>
                setPassword(e.target.value)
              }
              style={inputStyle}
            />
            <button
              disabled={busy}
              style={buttonStyle}
            >
              {busy
                ? "Working..."
                : "Login"}
            </button>
            <div style={{ marginTop: 8 }}>
              Token:{" "}
              {tokenShort ||
                "(none)"}
            </div>
          </form>
        </div>

        {/* QUERY */}
        <div style={cardStyle}>
          <h2>
            Run SQL or Ask Question
          </h2>
          <form onSubmit={onRun}>
            <textarea
              value={input}
              onChange={(e) =>
                setInput(e.target.value)
              }
              placeholder="SELECT ... OR ask: Top 5 countries by GDP"
              style={{
                ...inputStyle,
                height: 120,
                fontFamily:
                  "monospace",
              }}
            />
            <button
              disabled={busy}
              style={buttonStyle}
            >
              {busy
                ? "Running..."
                : "Run"}
            </button>
          </form>
        </div>

        {err && (
          <div style={errorStyle}>
            <strong>Error:</strong>
            <pre>{err}</pre>
          </div>
        )}

        {out && (
          <div style={responseStyle}>
            <ResultsTable result={out} />

            <details
              style={{ marginTop: 15 }}
            >
              <summary>
                Show Raw JSON
              </summary>
              <pre>
                {pretty(out)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}

/* =============================
   STYLES
============================= */

const pageStyle = {
  minHeight: "100vh",
  background: "#0b1220",
  color: "#e7eefc",
  padding: 24,
};

const cardStyle = {
  background: "#111a2e",
  borderRadius: 12,
  padding: 16,
  border:
    "1px solid #24304d",
  marginBottom: 20,
};

const inputStyle = {
  width: "100%",
  padding: 10,
  marginBottom: 10,
  borderRadius: 8,
  border:
    "1px solid #2a3a5e",
  background: "#0b1220",
  color: "#e7eefc",
  outline: "none",
};

const buttonStyle = {
  padding: 10,
  borderRadius: 8,
  cursor: "pointer",
  border:
    "1px solid #2a3a5e",
  background: "#1a2b55",
  color: "#e7eefc",
};

const errorStyle = {
  marginTop: 20,
  background: "#2a1220",
  padding: 12,
  borderRadius: 8,
};

const responseStyle = {
  marginTop: 20,
  background: "#0f1730",
  padding: 12,
  borderRadius: 8,
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
};

const thStyle = {
  padding: 10,
  borderBottom:
    "1px solid #2a3a5e",
  textAlign: "left",
};

const tdStyle = {
  padding: 10,
  borderBottom:
    "1px solid #24304d",
  fontFamily:
    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
};