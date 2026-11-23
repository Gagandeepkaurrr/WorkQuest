import { act, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useWorldCommand } from "./use-world-command";
import type { BranchState, CommandResponse } from "../../lib/types";
import { ApiError, write } from "../../lib/api-client";
vi.mock("../../lib/api-client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../lib/api-client")>()),
  write: vi.fn(),
}));
const state = { branch_id: "branch-a", state_revision: 7 } as BranchState;
const response = { ...state, state_revision: 8 } as CommandResponse;
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {children}
  </QueryClientProvider>
);
beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(write).mockReset();
});
describe("committed-command recovery", () => {
  it("reuses exact body and key across a timeout and reload, then updates from server", async () => {
    vi.mocked(write)
      .mockRejectedValueOnce(new TypeError("Lost response"))
      .mockResolvedValueOnce(response);
    const first = renderHook(() => useWorldCommand(state), { wrapper });
    await act(() => first.result.current.execute("checkout.restart", {}));
    expect(first.result.current.uncertain).toBe(true);
    const original = vi.mocked(write).mock.calls[0];
    first.unmount();
    const recovered = renderHook(
      () => useWorldCommand({ ...state, state_revision: 8 }),
      { wrapper },
    );
    await act(() => recovered.result.current.recover());
    expect(vi.mocked(write).mock.calls[1]).toEqual(original);
    expect(recovered.result.current.uncertain).toBe(false);
    expect(sessionStorage.getItem("wq:pending:branch-a")).toBeNull();
  });
  it("does not resend a rejected stale revision and does not carry uncertainty into another branch", async () => {
    vi.mocked(write).mockRejectedValueOnce(
      new ApiError("STALE_REVISION", "Refresh state", 409),
    );
    const hook = renderHook(({ current }) => useWorldCommand(current), {
      wrapper,
      initialProps: { current: state },
    });
    await act(() => hook.result.current.execute("checkout.restart", {}));
    expect(hook.result.current.uncertain).toBe(false);
    vi.mocked(write).mockRejectedValueOnce(new TypeError("Offline"));
    await act(() => hook.result.current.execute("checkout.restart", {}));
    hook.rerender({ current: { ...state, branch_id: "branch-b" } });
    expect(hook.result.current.uncertain).toBe(false);
    expect(sessionStorage.getItem("wq:pending:branch-a")).toBeTruthy();
  });
});
