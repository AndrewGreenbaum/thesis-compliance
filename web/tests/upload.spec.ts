import { test, expect } from "@playwright/test";

const spec = { name: "rackham", university: "University of Michigan", description: "Test rules", version: "1", rule_count: 1 };
const report = { pdf_name: "thesis.pdf", spec_name: "rackham", pages_checked: 1, rules_checked: 1, passed: false, error_count: 1, warning_count: 0,
  violations: [{ rule_id: "margin", rule_type: "margin", severity: "error", message: "Left margin too narrow", page: 1, expected: 1.5, found: 1, suggestion: "Adjust the left margin" }] };

test.beforeEach(async ({ page }) => {
  await page.route("**/specs", route => route.fulfill({ json: [spec] }));
  await page.goto("/check");
  await expect(page.getByRole("button", { name: /University of Michigan/ })).toBeVisible();
  await expect(page.getByText("Failed to connect to the server", { exact: false })).toHaveCount(0);
  await page.getByRole("button", { name: /University of Michigan/ }).click();
});

test("an invalid replacement clears the previous PDF", async ({ page }) => {
  const input = page.locator("#file-upload");
  await input.setInputFiles({ name: "thesis.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF") });
  await expect(page.getByRole("button", { name: "Check Compliance" })).toBeEnabled();
  await input.setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("text") });
  await expect(page.getByText("Please upload a PDF file", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload PDF and Select University" })).toBeDisabled();
});

test("a report uses the backend's lowercase severity", async ({ page }) => {
  await page.route("**/check", route => route.request().method() === "POST" ? route.fulfill({ json: report }) : route.continue());
  await page.locator("#file-upload").setInputFiles({ name: "thesis.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF") });
  await page.getByRole("button", { name: "Check Compliance" }).click();
  await expect(page.getByText("Left margin too narrow", { exact: true })).toBeVisible();
  await expect(page.getByText("Suggestion: Adjust the left margin", { exact: true })).toBeVisible();
});

test("starting over discards a late response", async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>(resolve => { release = resolve; });
  await page.route("**/check", async route => {
    if (route.request().method() !== "POST") return route.continue();
    await pending;
    await route.fulfill({ json: report }).catch(() => {});
  });
  await page.locator("#file-upload").setInputFiles({ name: "thesis.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF") });
  const request = page.waitForRequest(r => r.method() === "POST");
  await page.getByRole("button", { name: "Check Compliance" }).click();
  await request;
  await page.getByRole("button", { name: "Start Over" }).click();
  release();
  await expect(page.getByRole("heading", { name: "Check Your Thesis Formatting" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload PDF and Select University" })).toBeDisabled();
  await expect(page.getByText("Left margin too narrow", { exact: true })).toHaveCount(0);
});
