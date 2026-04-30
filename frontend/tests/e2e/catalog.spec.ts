import { test, expect } from "@playwright/test";

test("landing renders headline", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/Vinos con historia/i)).toBeVisible();
});
