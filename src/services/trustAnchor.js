/**
 * Resolves the trusted Ed25519 public key used to verify self-contained QRs.
 *
 * Trust is anchored in priority order:
 *   1. Build-time bundle — VITE_ED25519_PUBLIC_KEY_HEX baked into the app at
 *      `npm run build`. This is the strongest anchor: the key ships with the
 *      verifier and never needs the network.
 *   2. Local cache (trust-on-first-use) — a key fetched once from the public
 *      Trust Registry is cached in localStorage, so later scans verify offline.
 *   3. Live registry fetch — GET /public-keys/{key_id} the first time a key id
 *      is seen, then cached for (2). Requires the network exactly once per key.
 *
 * To bake a deploy-time anchor, fetch the deployed key id from
 * GET /public-keys, then build with:
 *   VITE_ED25519_PUBLIC_KEY_HEX=<hex> npm run build
 */
import { hexToBytes } from "./offlineVerify";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const BUNDLED_HEX = import.meta.env.VITE_ED25519_PUBLIC_KEY_HEX || "";
const CACHE_PREFIX = "qr_trust:";

function readCache(keyRef) {
  try {
    return localStorage.getItem(CACHE_PREFIX + keyRef) || "";
  } catch {
    return "";
  }
}

function writeCache(keyRef, hex) {
  try {
    localStorage.setItem(CACHE_PREFIX + keyRef, hex);
  } catch {
    /* private mode / storage disabled — non-fatal, just no caching */
  }
}

/**
 * Resolve the trusted public key for a QR's `qr_public_key_ref`.
 *
 * @param {string} keyRef            e.g. "ed25519:0123456789abcdef"
 * @param {object} [opts]
 * @param {boolean} [opts.allowFetch=true]  allow a one-time registry fetch
 * @returns {Promise<{bytes: Uint8Array, source: string}>}
 */
export async function getTrustedQrKey(keyRef, { allowFetch = true } = {}) {
  if (BUNDLED_HEX) {
    return { bytes: hexToBytes(BUNDLED_HEX), source: "bundled" };
  }

  const cached = readCache(keyRef);
  if (cached) {
    return { bytes: hexToBytes(cached), source: "cache" };
  }

  if (!allowFetch) {
    throw new Error("no trusted key available offline for " + keyRef);
  }

  const res = await fetch(`${API_BASE}/public-keys/${encodeURIComponent(keyRef)}`);
  if (!res.ok) {
    throw new Error(`trust registry lookup failed (${res.status}) for ${keyRef}`);
  }
  const data = await res.json();
  const hex = data.public_key_hex;
  if (!hex) {
    throw new Error("registry returned no public key for " + keyRef);
  }
  writeCache(keyRef, hex);
  return { bytes: hexToBytes(hex), source: "registry" };
}

/** Whether a deploy-time key is baked in (fully offline from first scan). */
export function hasBundledAnchor() {
  return Boolean(BUNDLED_HEX);
}
