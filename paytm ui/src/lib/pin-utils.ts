const HEX_LOOKUP = Array.from({ length: 256 }).map((_, index) => index.toString(16).padStart(2, "0"));

function bytesToHex(bytes: Uint8Array): string {
  let out = "";
  for (let i = 0; i < bytes.length; i += 1) {
    out += HEX_LOOKUP[bytes[i]];
  }
  return out;
}

export async function sha256(input: string): Promise<string> {
  if (typeof crypto === "undefined" || !crypto.subtle) {
    throw new Error("SHA-256 is unavailable in this runtime");
  }

  const encoded = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest("SHA-256", encoded);
  return bytesToHex(new Uint8Array(hash));
}

export async function hashPin(pin: string): Promise<string> {
  if (!/^\d{4}$/.test(pin)) {
    throw new Error("PIN must be exactly 4 digits");
  }
  return sha256(pin);
}

export async function verifyPin(pin: string, expectedHash: string): Promise<boolean> {
  const hashed = await hashPin(pin);
  return hashed === expectedHash;
}

export function createPinVerifiedUntil(minutes = 15): string {
  return new Date(Date.now() + minutes * 60 * 1000).toISOString();
}

export function isPinVerificationValid(pinVerifiedUntil?: string | null): boolean {
  if (!pinVerifiedUntil) {
    return false;
  }
  return new Date(pinVerifiedUntil).getTime() > Date.now();
}
