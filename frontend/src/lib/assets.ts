const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

const DEFAULT_ASSET_BASE_URL = API_BASE_URL.replace(/\/api\/v\d+\/?$/, "");
const ASSET_BASE_URL = import.meta.env.VITE_ASSET_BASE_URL || DEFAULT_ASSET_BASE_URL;

export const FALLBACK_WINE_IMAGE =
  "/wine-placeholder.svg";

export function resolveAssetUrl(value?: string | null): string | null {
  const rawValue = value?.trim();
  if (!rawValue) {
    return null;
  }

  if (/^(https?:|data:|blob:)/i.test(rawValue)) {
    return rawValue;
  }

  if (rawValue.startsWith("//")) {
    return `https:${rawValue}`;
  }

  const baseUrl = ASSET_BASE_URL.replace(/\/+$/, "");
  const path = rawValue.startsWith("/") ? rawValue : `/${rawValue}`;
  return `${baseUrl}${path}`;
}

export function wineImageSrc(value?: string | null): string {
  return resolveAssetUrl(value) ?? FALLBACK_WINE_IMAGE;
}

export function applyWineImageFallback(event: { currentTarget: HTMLImageElement }) {
  const image = event.currentTarget;
  if (image.getAttribute("src") !== FALLBACK_WINE_IMAGE) {
    image.src = FALLBACK_WINE_IMAGE;
  }
}
