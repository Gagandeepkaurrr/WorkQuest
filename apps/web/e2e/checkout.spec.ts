import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { signup, choose, openEvidence, action, activate } from "./helpers";
test("checkout UI, persisted notes, mock chat, replay and branch", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Less watching/ }),
  ).toBeVisible();
  if (testInfo.project.name === "desktop") await signup(page);
  else
    await activate(
      page.getByRole("button", { name: "Try the demo", exact: true }),
    );
  await expect(
    page.getByRole("heading", { name: "Your next good decision." }),
  ).toBeVisible();
  await page.screenshot({
    path: `../../artifacts/library-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await activate(
    page
      .locator("article")
      .filter({
        has: page.getByRole("heading", { name: "The checkout that stopped." }),
      })
      .getByRole("link", { name: "View mission" }),
  );
  await activate(page.getByRole("button", { name: "Enter the workplace" }));
  await expect(
    page.getByRole("heading", { name: "A team to think with." }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Message your teammate" })
    .fill("Which evidence should I inspect?");
  await activate(page.getByRole("button", { name: "Send", exact: true }));
  await expect(page.locator(".message.assistant").last()).toContainText(
    "Open an artifact",
    { timeout: 20000 },
  );
  await activate(page.getByRole("button", { name: "Tasks", exact: true }));
  await choose(page.getByLabel("Next step"), "evidence.open");
  await activate(page.getByRole("button", { name: "Send structured update" }));
  await expect(
    page.getByRole("status").filter({ hasText: "Decision recorded" }),
  ).toBeVisible();
  await openEvidence(page, "Checkout error logs");
  await action(page, "Set coupon feature flag", "false");
  await openEvidence(page, "Coupon configuration & contract");
  await action(page, "Publish reviewed configuration");
  await action(page, "Refresh shared configuration cache");
  await action(page, "Set coupon feature flag", "true");
  await action(page, "Test the v2 coupon contract");
  await action(page, "Observe two workload ticks");
  await activate(page.getByRole("button", { name: "Notes", exact: true }));
  await page
    .getByLabel("Your investigation notes")
    .fill("Origin and cache must agree.");
  await activate(page.getByRole("button", { name: "Save notes" }));
  await page.reload();
  await expect(page.getByLabel("Your investigation notes")).toHaveValue(
    "Origin and cache must agree.",
  );
  await activate(page.getByRole("button", { name: "Tasks", exact: true }));
  await choose(
    page.getByRole("combobox", { name: "Diagnosis", exact: true }),
    "The rollout omitted its configuration-contract migration",
  );
  await activate(page.getByRole("button", { name: "Record hypothesis" }));
  await choose(
    page.getByRole("combobox", { name: "Outcome", exact: true }),
    "successful",
  );
  await activate(page.getByRole("button", { name: "Record final recap" }));
  await activate(
    page.getByRole("button", { name: "Finish attempt", exact: true }),
  );
  await activate(
    page.getByRole("button", { name: "Finish and view assessment" }),
  );
  await expect(
    page.getByRole("heading", { name: "Every decision teaches you." }),
  ).toBeVisible();
  await expect(page.locator(".score-display").first()).toContainText("100");
  await activate(page.getByRole("button", { name: "Verify recorded replay" }));
  await expect(
    page.getByRole("status").filter({ hasText: "Replay matches" }),
  ).toBeVisible();
  await page.screenshot({
    path: `../../artifacts/debrief-${testInfo.project.name}.png`,
    fullPage: true,
  });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations).toEqual([]);
  if (testInfo.project.name === "desktop") {
    await activate(page.getByRole("button", { name: "Share report" }));
    await page.getByLabel("Optional public alias").fill("Practice learner");
    await activate(
      page.getByRole("button", { name: "Preview exact public fields" }),
    );
    await activate(page.getByRole("button", { name: /Create public link/ }));
    const url = await page.getByLabel("Your public link").inputValue();
    const publicPage = await page.context().newPage();
    await publicPage.goto(url);
    await expect(publicPage.locator(".score-display")).toContainText("100");
    await expect(publicPage.locator("body")).not.toContainText(
      "Origin and cache must agree.",
    );
    await activate(page.getByRole("button", { name: "Revoke link now" }));
    await publicPage.reload();
    await expect(
      publicPage.getByRole("heading", { name: "This report is unavailable." }),
    ).toBeVisible();
    await publicPage.close();
  }
  await activate(
    page.getByRole("button", { name: "Checkpoints & approaches" }),
  );
  await page
    .getByRole("dialog")
    .getByLabel("Name your next approach")
    .fill("Try another path");
  const cp = page
    .getByRole("dialog")
    .locator("article")
    .filter({ hasText: "Mission start" });
  await activate(cp.getByRole("button", { name: "Try from here" }));
  await expect(
    page.getByRole("heading", { name: "The checkout that stopped." }),
  ).toBeVisible();
  await expect(page.locator(".clock-pill strong")).toHaveText("0");
  await action(page, "Set coupon feature flag", "false");
  await activate(
    page.getByRole("button", { name: "Finish attempt", exact: true }),
  );
  await activate(
    page.getByRole("button", { name: "Finish and view assessment" }),
  );
  await activate(
    page.getByRole("button", { name: "Checkpoints & approaches" }),
  );
  await activate(page.getByRole("link", { name: "Compare played branches" }));
  await expect(
    page.getByRole("heading", { name: "The difference a decision makes." }),
  ).toBeVisible();
  await expect(page.locator(".comparison-grid article")).toHaveCount(2);
  await expect(page.locator("body")).toHaveJSProperty(
    "scrollWidth",
    await page.evaluate(() => window.innerWidth),
  );
});
