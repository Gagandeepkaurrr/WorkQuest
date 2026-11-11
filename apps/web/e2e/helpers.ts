import { expect, type Page, type Locator } from "@playwright/test";
export async function choose(select: Locator, value: string) {
  await expect(select).toBeVisible();
  await expect.poll(() => select.locator("option").count()).toBeGreaterThan(0);
  const index = await select
    .locator("option")
    .evaluateAll(
      (options, value) =>
        options.findIndex(
          (o) =>
            (o as HTMLOptionElement).value === value || o.textContent === value,
        ),
      value,
    );
  expect(index).toBeGreaterThanOrEqual(0);
  const option = select.locator("option").nth(index);
  const expected =
    (await option.getAttribute("value")) ?? (await option.textContent()) ?? "";
  const text = (await option.textContent()) ?? "";
  await select.focus();
  await select.pressSequentially(text);
  await select.press("Tab");
  await expect(select).toHaveValue(expected);
}
export async function activate(control: Locator) {
  await expect(control).toBeEnabled();
  await control.press("Enter");
}
export async function signup(page: Page) {
  const email = `ui-${crypto.randomUUID()}@example.com`;
  await page.goto("/sign-up");
  await page.getByLabel("Your name").fill("UI Learner");
  await page.getByLabel("Email address").fill(email);
  await page
    .getByLabel("Password", { exact: true })
    .fill("locally verified long passphrase");
  await activate(page.getByRole("button", { name: "Create your account" }));
  await expect(page.getByRole("status")).toContainText("email");
  let messageId = "";
  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          "http://localhost:8025/api/v1/messages?limit=100",
        );
        const data = (await response.json()) as {
          messages: { ID: string; To: { Address: string }[] }[];
        };
        messageId =
          data.messages.find((m) => m.To.some((t) => t.Address === email))
            ?.ID ?? "";
        return Boolean(messageId);
      },
      { timeout: 30000 },
    )
    .toBeTruthy();
  const response = await page.request.get(
    `http://localhost:8025/api/v1/message/${messageId}`,
  );
  const mail = (await response.json()) as { Text: string };
  const link = mail.Text.match(
    /http:\/\/localhost:5173\/verify-email\?token=[\w-]+/,
  )?.[0];
  expect(link).toBeTruthy();
  await page.goto(link!);
  await expect(page.getByRole("status")).toContainText("verified");
  await activate(page.getByRole("link", { name: /Continue to sign in/ }));
  await page.getByLabel("Email address").fill(email);
  await page
    .getByLabel("Password", { exact: true })
    .fill("locally verified long passphrase");
  await activate(page.getByRole("button", { name: "Sign in", exact: true }));
  await expect(
    page.getByRole("heading", { name: "Your next good decision." }),
  ).toBeVisible();
  return email;
}
export async function openEvidence(page: Page, title: string) {
  await activate(page.getByRole("button", { name: "Evidence", exact: true }));
  const card = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await activate(card.getByRole("button", { name: "Inspect evidence" }));
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
}
export async function action(page: Page, name: string, value?: string) {
  await activate(page.getByRole("button", { name: "Actions", exact: true }));
  const card = page
    .locator("article")
    .filter({ has: page.getByRole("heading", { name, exact: true }) });
  await activate(card.getByRole("button", { name: "Review operation" }));
  if (value)
    await choose(page.getByRole("dialog").getByRole("combobox"), value);
  await activate(
    page.getByRole("button", { name: "Continue to confirmation" }),
  );
  await activate(
    page.getByRole("button", { name: "Execute simulated operation" }),
  );
  await expect(page.getByRole("dialog")).toBeHidden();
}
