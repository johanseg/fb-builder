const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function resolveMediaUrl(url, apiUrl = API_URL) {
  if (!url || typeof url !== 'string' || !url.startsWith('/uploads/')) {
    return url;
  }

  return new URL(url, apiUrl).toString();
}
