export interface RuntimeEnvironment {
  API_INTERNAL_BASE_URL?: string;
  API_BASE_URL?: string;
  NODE_ENV?: string;
}

const LOCAL_API_BASE_URL = "http://localhost:8000";

export function resolveApiBaseUrl(environment: RuntimeEnvironment): string {
  const internalBaseUrl = environment.API_INTERNAL_BASE_URL?.trim();
  const publicBaseUrl = environment.API_BASE_URL?.trim();

  if (environment.NODE_ENV === "development" && internalBaseUrl === "http://api:8000") {
    return publicBaseUrl || LOCAL_API_BASE_URL;
  }

  return internalBaseUrl || publicBaseUrl || LOCAL_API_BASE_URL;
}
