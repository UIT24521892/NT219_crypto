/**
 * High-level entry point the UI calls with a scanned/pasted QR string.
 *
 * Ties together payload parsing, trust-anchor resolution and offline Ed25519
 * verification. Verification itself never touches the network; the only
 * possible network call is a one-time Trust Registry lookup to learn a public
 * key the device has not seen before (skipped entirely when a key is bundled at
 * build time or already cached). Pass `allowFetch: false` to force a strictly
 * offline check.
 */
import { parseQrPayload, verifyQrOffline } from "./offlineVerify";
import { getTrustedQrKey } from "./trustAnchor";

const REASON_TEXT = {
  ok: "Chữ ký hợp lệ — tài liệu xác thực (xác minh offline bằng Ed25519).",
  expired: "Chữ ký đúng nhưng QR đã hết hạn.",
  not_yet_valid: "Chữ ký đúng nhưng QR chưa tới thời điểm hiệu lực.",
  bad_signature: "Chữ ký KHÔNG hợp lệ — QR đã bị sửa hoặc sai khoá.",
  malformed: "Mã QR không đúng định dạng tự chứa (self-contained).",
  verify_error: "Không thể xác minh trên trình duyệt này.",
  no_trust_key: "Không tìm thấy khoá công khai tin cậy để xác minh.",
};

/**
 * @param {string} payload  the scanned QR string (b64url(sig)|<canonical>)
 * @param {object} [opts]
 * @param {Date}    [opts.now]
 * @param {boolean} [opts.allowFetch=true]  allow a one-time registry lookup
 * @returns {Promise<object>} { valid, reason, message, fields, keySource }
 */
export async function verifyScannedQr(payload, { now = new Date(), allowFetch = true } = {}) {
  let parsed;
  try {
    parsed = parseQrPayload(payload);
  } catch (e) {
    return { valid: false, reason: "malformed", message: REASON_TEXT.malformed, detail: e.message };
  }

  const keyRef = parsed.fields.qr_public_key_ref;
  let key;
  try {
    key = await getTrustedQrKey(keyRef, { allowFetch });
  } catch (e) {
    return {
      valid: false,
      reason: "no_trust_key",
      message: REASON_TEXT.no_trust_key,
      detail: e.message,
      fields: parsed.fields,
    };
  }

  const result = await verifyQrOffline(payload, key.bytes, now);
  return {
    ...result,
    message: REASON_TEXT[result.reason] || result.reason,
    keySource: key.source,
  };
}
