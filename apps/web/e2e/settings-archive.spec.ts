import { test, expect } from "@playwright/test";
import { activate, choose, signup } from "./helpers";

test("preferences persist and archived runs make room for another mission", async ({
  page,
}) => {
  await signup(page);
  await page.goto("/settings");
  await page.getByLabel("Display name").fill("Curious Learner");
  await activate(page.getByRole("button", { name: "Save profile" }));
  await expect(page.getByRole("status")).toHaveText("Profile saved.");
  await choose(page.getByLabel("Color theme"), "dark");
  await expect(page.getByRole("status")).toHaveText("Theme saved.");
  await page.getByLabel("Reduce motion").focus();
  await page.getByLabel("Reduce motion").press("Space");
  await expect(page.getByRole("status")).toHaveText("Motion preference saved.");
  await page.reload();
  await expect(page.getByLabel("Display name")).toHaveValue("Curious Learner");
  await expect(page.getByLabel("Color theme")).toHaveValue("dark");
  await expect(page.getByLabel("Reduce motion")).toBeChecked();
  await choose(page.getByLabel("Color theme"), "light");
  await page.goto("/missions/checkout-outage");
  await activate(page.getByRole("button", { name: "Enter the workplace" }));
  await expect(
    page.getByRole("heading", { name: "A team to think with." }),
  ).toBeVisible();
  await page.goto("/missions");
  await activate(
    page.getByRole("button", { name: "Archive The checkout that stopped." }),
  );
  await expect(page.getByText("Archived", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Archived", { exact: true })).toBeVisible();
  await page.goto("/missions/checkout-outage");
  await activate(page.getByRole("button", { name: "Enter the workplace" }));
  await expect(
    page.getByRole("heading", { name: "A team to think with." }),
  ).toBeVisible();
  await page.goto("/settings");
  await activate(
    page.getByRole("button", { name: "Delete account", exact: true }),
  );
  const dialog = page.getByRole("dialog");
  await dialog
    .getByLabel("Current password")
    .fill("locally verified long passphrase");
  await dialog.getByLabel("Type DELETE to confirm").fill("DELETE");
  await activate(
    dialog.getByRole("button", { name: "Permanently delete account" }),
  );
  await expect(
    page.getByRole("heading", { name: /Less watching/ }),
  ).toBeVisible();
});
