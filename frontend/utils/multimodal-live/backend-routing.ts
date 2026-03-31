const LOCAL_BACKEND_WS_URL = "ws://localhost:8000/ws";
const DEFAULT_BACKEND_WS_URL = "wss://voice-agent-backend-o4dv7heaia-uc.a.run.app/ws";
const STAGING_BACKEND_WS_URL = "wss://voice-agent-backend-staging-o4dv7heaia-uc.a.run.app/ws";

const BACKEND_WS_QUERY_PARAM_KEYS = ["backend_ws_url", "backend_url", "ws_url"];
const BACKEND_TARGET_QUERY_PARAM_KEYS = ["backend", "backend_env"];
const STAGING_FRONTEND_HOSTS = new Set([
  "va-staging-483614.web.app",
  "va-staging-483614.firebaseapp.com",
]);
const LOCAL_FRONTEND_HOSTS = new Set(["localhost", "127.0.0.1"]);

const readQueryParam = (params: URLSearchParams, keys: string[]) => {
  for (const key of keys) {
    const value = params.get(key);
    if (value) {
      return value;
    }
  }
  return undefined;
};

const resolveNamedBackendTarget = (
  target: string | undefined,
  defaultWsUrl: string,
) => {
  if (!target) {
    return undefined;
  }

  switch (target.trim().toLowerCase()) {
    case "staging":
      return STAGING_BACKEND_WS_URL;
    case "prod":
    case "production":
      return defaultWsUrl;
    case "local":
    case "localhost":
      return LOCAL_BACKEND_WS_URL;
    default:
      return undefined;
  }
};

export const copyBackendRoutingQueryParams = (
  source: URLSearchParams,
  target: URLSearchParams,
) => {
  const explicitWsUrl = readQueryParam(source, BACKEND_WS_QUERY_PARAM_KEYS);
  if (explicitWsUrl) {
    target.set(BACKEND_WS_QUERY_PARAM_KEYS[0], explicitWsUrl);
  }

  const namedTarget = readQueryParam(source, BACKEND_TARGET_QUERY_PARAM_KEYS);
  if (namedTarget) {
    target.set(BACKEND_TARGET_QUERY_PARAM_KEYS[0], namedTarget);
  }
};

export const resolveBackendWebSocketUrl = (defaultWsUrl?: string) => {
  const fallbackWsUrl = defaultWsUrl?.trim() || DEFAULT_BACKEND_WS_URL;

  if (typeof window === "undefined") {
    return fallbackWsUrl;
  }

  const params = new URLSearchParams(window.location.search);
  const explicitWsUrl = readQueryParam(params, BACKEND_WS_QUERY_PARAM_KEYS);
  if (explicitWsUrl) {
    return explicitWsUrl;
  }

  const namedTarget = resolveNamedBackendTarget(
    readQueryParam(params, BACKEND_TARGET_QUERY_PARAM_KEYS),
    fallbackWsUrl,
  );
  if (namedTarget) {
    return namedTarget;
  }

  const hostname = window.location.hostname.toLowerCase();
  if (LOCAL_FRONTEND_HOSTS.has(hostname)) {
    return LOCAL_BACKEND_WS_URL;
  }

  if (STAGING_FRONTEND_HOSTS.has(hostname)) {
    return STAGING_BACKEND_WS_URL;
  }

  return fallbackWsUrl;
};

export const getBackendHttpBaseUrl = (wsUrl: string) => {
  const parsed = new URL(
    wsUrl,
    typeof window === "undefined" ? "http://localhost" : window.location.origin,
  );

  parsed.protocol = parsed.protocol === "wss:" ? "https:" : "http:";
  parsed.pathname = parsed.pathname.replace(/\/ws\/?$/, "") || "/";
  parsed.search = "";
  parsed.hash = "";

  return parsed.toString().replace(/\/$/, "");
};
