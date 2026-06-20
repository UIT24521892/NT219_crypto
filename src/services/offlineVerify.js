/**
 * Offline, on-the-spot verification of a self-contained QR (Ed25519).
 *
 * The QR is NOT a URL — it is a self-contained, pipe-delimited string that can
 * be verified without contacting the server (like a paper travel permit):
 *
 *     payload   = b64url(signature) | <canonical>
 *     canonical = doc_id | file_hash | signer_email | signed_at | valid_from
 *               | valid_until | qr_public_key_ref
 *
 * The Ed25519 signature covers the UTF-8 bytes of <canonical>. A verifier
 * rebuilds the signed bytes by dropping the first field and re-joining the rest
 * — no date re-formatting, no re-encoding — so the bytes match the signer's
 * exactly. Verification uses the Web Crypto API (Ed25519); no network, no
 * third-party library.
 *
 * NOTE (honesty for the defense): Ed25519 is a *classical* signature, not
 * post-quantum. This layer is a fast offline-UX convenience. The post-quantum
 * integrity guarantee comes from ML-DSA-44, verified online via /verify or from
 * the signed PDF metadata.
 */

const FIELD_SEP = "|";

const FIELD_NAMES = [
  "doc_id",
  "file_hash",
  "signer_email",
  "signed_at",
  "valid_from",
  "valid_until",
  "qr_public_key_ref",
];

/** Decode unpadded URL-safe Base64 to a Uint8Array. */
export function b64urlToBytes(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") +
    "=".repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/** Decode a hex string (e.g. the trust-registry public key) to a Uint8Array. */
export function hexToBytes(hex) {
  const clean = hex.trim().toLowerCase();
  if (clean.length % 2 !== 0 || /[^0-9a-f]/.test(clean)) {
    throw new Error("invalid hex");
  }
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < bytes.length; i += 1) {
    bytes[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

/**
 * Split a self-contained QR string into its parts.
 * Returns { signature: Uint8Array, canonical: string, canonicalBytes, fields }.
 */
export function parseQrPayload(payload) {
  if (typeof payload !== "string" || !payload.includes(FIELD_SEP)) {
    throw new Error("not a self-contained QR payload");
  }
  const sepIndex = payload.indexOf(FIELD_SEP);
  const sigField = payload.slice(0, sepIndex);
  const canonical = payload.slice(sepIndex + 1);

  const parts = canonical.split(FIELD_SEP);
  if (parts.length !== FIELD_NAMES.length) {
    throw new Error("malformed QR canonical");
  }
  const fields = {};
  FIELD_NAMES.forEach((name, i) => {
    fields[name] = parts[i];
  });

  return {
    signature: b64urlToBytes(sigField),
    canonical,
    canonicalBytes: new TextEncoder().encode(canonical),
    fields,
  };
}

/** Is Ed25519 verification available in this browser/runtime? */
export async function isOfflineVerifySupported() {
  try {
    const subtle = globalThis.crypto?.subtle;
    if (!subtle) return false;
    await subtle.importKey("raw", new Uint8Array(32), { name: "Ed25519" }, false, [
      "verify",
    ]);
    return true;
  } catch {
    return false;
  }
}

/**
 * Verify a self-contained QR payload entirely offline.
 *
 * @param {string} payload            the scanned QR string
 * @param {Uint8Array} publicKeyBytes the trusted Ed25519 public key (32 bytes)
 * @param {Date} [now]                clock for the validity-window check
 * @returns {Promise<object>} structured result
 */
export async function verifyQrOffline(payload, publicKeyBytes, now = new Date()) {
  let parsed;
  try {
    parsed = parseQrPayload(payload);
  } catch (e) {
    return { valid: false, reason: "malformed", detail: e.message };
  }

  const { signature, canonicalBytes, fields } = parsed;

  let signatureValid = false;
  try {
    const key = await globalThis.crypto.subtle.importKey(
      "raw",
      publicKeyBytes,
      { name: "Ed25519" },
      false,
      ["verify"]
    );
    signatureValid = await globalThis.crypto.subtle.verify(
      { name: "Ed25519" },
      key,
      signature,
      canonicalBytes
    );
  } catch (e) {
    return { valid: false, reason: "verify_error", detail: e.message, fields };
  }

  if (!signatureValid) {
    return { valid: false, reason: "bad_signature", fields };
  }

  // Signature is authentic — now check the validity window.
  const validFrom = new Date(fields.valid_from);
  const validUntil = new Date(fields.valid_until);
  if (now < validFrom) {
    return { valid: false, reason: "not_yet_valid", fields, validFrom, validUntil };
  }
  if (now > validUntil) {
    return { valid: false, reason: "expired", fields, validFrom, validUntil };
  }

  return { valid: true, reason: "ok", fields, validFrom, validUntil };
}

export const OFFLINE_VERIFY_FIELD_NAMES = FIELD_NAMES;
