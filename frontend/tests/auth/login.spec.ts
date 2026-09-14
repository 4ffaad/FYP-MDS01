import { test, expect } from "@playwright/test";

test("registration, refresh, readable errors, login and logout use the backend session", async ({
  page,
}) => {
  let signedIn = false;
  let registerRequestUrl = "";
  await page.route("**/api/auth/session", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: signedIn,
        mode: "local-accounts",
        user: signedIn
          ? {
              id: "USR-TEST",
              email: "teammate@example.test",
              display_name: "teammate",
            }
          : null,
      }),
    });
  });
  await page.route("**/api/auth/register", async (route) => {
    registerRequestUrl = route.request().url();
    signedIn = true;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: true,
        user: {
          id: "USR-TEST",
          email: "teammate@example.test",
          display_name: "teammate",
        },
      }),
    });
  });
  await page.route("**/api/auth/login", async (route) => {
    const body = JSON.parse(route.request().postData() ?? "{}");
    if (body.password !== "correct horse battery") {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Email or password is incorrect." }),
      });
      return;
    }
    signedIn = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: true,
        user: {
          id: "USR-TEST",
          email: "teammate@example.test",
          display_name: "teammate",
        },
      }),
    });
  });
  await page.route("**/api/auth/logout", async (route) => {
    signedIn = false;
    await route.fulfill({ status: 204, body: "" });
  });

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login/);
  await page.getByRole("button", { name: "Create an account" }).click();
  await page.getByLabel("Email address").fill("teammate@example.test");
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  expect(registerRequestUrl).toMatch(
    /^http:\/\/localhost:8000\/api\/auth\/register/,
  );
  await expect(page.getByTitle("teammate@example.test")).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "EEG analysis" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Email address").fill("teammate@example.test");
  await page.getByLabel("Password").fill("wrong password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Email or password is incorrect." }),
  ).toBeVisible();
  await page.getByLabel("Password").fill("correct horse battery");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
});
