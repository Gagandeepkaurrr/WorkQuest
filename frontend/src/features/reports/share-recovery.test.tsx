import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ShareDialog } from "./share-dialog";
afterEach(() => sessionStorage.clear());
it("keeps the previously approved alias and expiry visible during uncertain share recovery", () => {
  sessionStorage.setItem(
    "wq:request:share:one",
    JSON.stringify({
      path: "/branches/one/shares",
      body: { alias: "Approved alias", expiry_days: 1 },
      key: "original-key",
    }),
  );
  render(<ShareDialog branchId="one" />);
  fireEvent.click(screen.getByRole("button", { name: "Share report" }));
  expect(screen.getByLabelText("Optional public alias")).toHaveValue(
    "Approved alias",
  );
  expect(screen.getByLabelText("Optional public alias")).toBeDisabled();
  expect(screen.getByLabelText("Link expires after")).toHaveValue("1");
  expect(
    screen.getByRole("button", { name: "Recover existing share link" }),
  ).toBeVisible();
});
