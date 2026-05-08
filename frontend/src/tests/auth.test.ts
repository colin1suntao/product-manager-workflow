import { describe, it, expect, beforeEach } from "vitest";
import {
  setTokens,
  getAccessToken,
  getRefreshToken,
  clearTokens,
  isTokenExpired,
} from "@/lib/auth";

describe("auth module", () => {
  beforeEach(() => {
    clearTokens();
  });

  it("stores and retrieves access token", () => {
    setTokens("access-123", "refresh-456");
    expect(getAccessToken()).toBe("access-123");
  });

  it("stores and retrieves refresh token", () => {
    setTokens("access-123", "refresh-456");
    expect(getRefreshToken()).toBe("refresh-456");
  });

  it("clears all tokens", () => {
    setTokens("access-123", "refresh-456");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("detects expired token", () => {
    // Create a token that expired 1 hour ago
    const now = Math.floor(Date.now() / 1000);
    const expiredPayload = btoa(JSON.stringify({ exp: now - 3600 }));
    const expiredToken = `header.${expiredPayload}.signature`;
    expect(isTokenExpired(expiredToken)).toBe(true);
  });

  it("detects valid token", () => {
    // Create a token that expires in 1 hour
    const now = Math.floor(Date.now() / 1000);
    const validPayload = btoa(JSON.stringify({ exp: now + 3600 }));
    const validToken = `header.${validPayload}.signature`;
    expect(isTokenExpired(validToken)).toBe(false);
  });

  it("returns false for malformed token", () => {
    expect(isTokenExpired("malformed")).toBe(true);
  });
});
