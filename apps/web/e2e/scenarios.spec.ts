import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import { signup, choose, openEvidence, action, activate } from "./helpers";
type Definition = {
  metadata: { title: string };
  rubric: { cause_id: string };
  artifacts: { id: string; title: string }[];
  action_catalog: { id: string; label: string; title?: string }[];
  golden_commands: { type: string; payload: Record<string, unknown> }[];
  golden_expected: { simulation_time: number };
};
for (const slug of ["inventory-race", "analytics-timezone"]) {
  test(`${slug} complete through the UI`, async ({ page }, testInfo) => {
    const d = JSON.parse(
      readFileSync(`../api/content/scenarios/${slug}/scenario.json`, "utf8"),
    ) as Definition;
    await signup(page);
    await activate(
      page
        .locator("article")
        .filter({
          has: page.getByRole("heading", {
            name: d.metadata.title,
            exact: true,
          }),
        })
        .getByRole("link", { name: "View mission" }),
    );
    await activate(page.getByRole("button", { name: "Enter the workplace" }));
    await activate(page.getByRole("button", { name: "Tasks", exact: true }));
    await choose(page.getByLabel("Next step"), "evidence.open");
    await activate(
      page.getByRole("button", { name: "Send structured update" }),
    );
    for (const c of d.golden_commands) {
      if (c.type === "evidence.open")
        await openEvidence(
          page,
          d.artifacts.find((a) => a.id === c.payload.artifact_id)!.title,
        );
      else {
        const a = d.action_catalog.find((a) => a.id === c.type)!;
        const value = Object.values(c.payload)[0];
        await action(
          page,
          a.label,
          value === undefined ? undefined : String(value),
        );
      }
    }
    await expect(page.locator(".clock-pill strong")).toHaveText(
      String(d.golden_expected.simulation_time),
    );
    await activate(page.getByRole("button", { name: "Tasks", exact: true }));
    await choose(
      page.getByRole("combobox", { name: "Diagnosis", exact: true }),
      d.rubric.cause_id,
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
    await expect(page.locator(".score-display").first()).toContainText("100");
    await activate(
      page.getByRole("button", { name: "Verify recorded replay" }),
    );
    await expect(
      page.getByRole("status").filter({ hasText: "Replay matches" }),
    ).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({
      path: `../../artifacts/${slug}-${testInfo.project.name}.png`,
      fullPage: true,
    });
  });
}
