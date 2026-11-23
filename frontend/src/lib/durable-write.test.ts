import { beforeEach, expect, it, vi } from "vitest";
import { durableWrite, pendingWrite } from "./durable-write";
import { ApiError, write } from "./api-client";
vi.mock("./api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api-client")>()),
  write: vi.fn(),
}));
beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(write).mockReset();
});
it("recovers the original secret-bearing request after a lost response", async () => {
  vi.mocked(write)
    .mockRejectedValueOnce(new TypeError("Lost response"))
    .mockResolvedValueOnce({ url: "https://example.com/report/token" });
  await expect(
    durableWrite("share:one", "/branches/one/shares", {
      alias: "Original",
      expiry_days: 1,
    }),
  ).rejects.toThrow();
  const first = vi.mocked(write).mock.calls[0];
  expect(pendingWrite("share:one")?.body).toEqual({
    alias: "Original",
    expiry_days: 1,
  });
  await durableWrite("share:one", "/branches/one/shares", {
    alias: "Changed",
    expiry_days: 30,
  });
  expect(vi.mocked(write).mock.calls[1]).toEqual(first);
  expect(pendingWrite("share:one")).toBeNull();
});
it("clears a definitively expired result so a new explicit share can be made", async () => {
  vi.mocked(write).mockRejectedValueOnce(
    new ApiError("RESULT_EXPIRED", "Expired", 410),
  );
  await expect(
    durableWrite("share:one", "/branches/one/shares", {}),
  ).rejects.toThrow();
  expect(pendingWrite("share:one")).toBeNull();
});
it.each([401, 403, 429])(
  "preserves the original key when replay is rejected before lookup (%s)",
  async (status) => {
    vi.mocked(write)
      .mockRejectedValueOnce(new TypeError("Lost response"))
      .mockRejectedValueOnce(new ApiError("RETRY", "Retry later", status))
      .mockResolvedValueOnce({ ok: true });
    await expect(durableWrite("run:one", "/runs", {})).rejects.toThrow();
    const original = vi.mocked(write).mock.calls[0];
    await expect(durableWrite("run:one", "/runs", {})).rejects.toThrow();
    expect(pendingWrite("run:one")).not.toBeNull();
    await durableWrite("run:one", "/runs", {});
    expect(vi.mocked(write).mock.calls[2]).toEqual(original);
  },
);
