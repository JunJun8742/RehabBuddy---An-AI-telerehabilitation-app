import { describe, expect, it, vi, beforeEach } from "vitest";
import { api, ApiError, clearToken, getToken, setToken } from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    clearToken();
  });

  it("sends the bearer token when one is stored", async () => {
    setToken("abc");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    const result = await api<{ ok: boolean }>("/health");
    expect(result).toEqual({ ok: true });
    const [, init] = fetchMock.mock.calls[0];
    expect((init!.headers as Record<string, string>)["Authorization"]).toBe("Bearer abc");
  });

  it("throws ApiError with the status on non-2xx", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("nope", { status: 409 }));
    await expect(api("/auth/register", { method: "POST" })).rejects.toBeInstanceOf(ApiError);
    await expect(api("/auth/register", { method: "POST" })).rejects.toMatchObject({ status: 409 });
  });

  it("clears the stored token on 401", async () => {
    setToken("stale");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 401 }));
    await expect(api("/auth/me")).rejects.toMatchObject({ status: 401 });
    expect(getToken()).toBeNull();
  });
});
