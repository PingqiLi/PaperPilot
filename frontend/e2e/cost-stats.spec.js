import { test, expect } from '@playwright/test'

test.describe('Cost stats page', () => {
  test('shows page heading', async ({ page }) => {
    await page.goto('/stats')
    await expect(page.locator('h1', { hasText: 'Cost Stats' })).toBeVisible()
    await expect(page.locator('text=LLM API usage and cost tracking')).toBeVisible()
  })

  test('shows summary cards', async ({ page }) => {
    await page.goto('/stats')
    await expect(page.locator('text=Total Cost')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=Total Tokens')).toBeVisible()
  })

  test('shows chart section with controls', async ({ page }) => {
    await page.goto('/stats')
    await expect(page.locator('text=Daily Usage')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('button', { hasText: 'Cost' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Tokens' })).toBeVisible()
    await expect(page.locator('button', { hasText: '7d' })).toBeVisible()
  })

  test('shows empty state when no usage data', async ({ page }) => {
    await page.goto('/stats')
    await expect(page.locator('text=No usage data yet')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=No requests yet')).toBeVisible()
  })

  test('shows request history section', async ({ page }) => {
    await page.goto('/stats')
    await expect(page.locator('text=Request History')).toBeVisible({ timeout: 5000 })
  })

  test('toggles time range filter', async ({ page }) => {
    await page.goto('/stats')
    await page.locator('button', { hasText: '30d' }).click()
    await expect(page.locator('text=Daily Usage')).toBeVisible()
    await page.locator('button', { hasText: '1d' }).click()
    await expect(page.locator('text=Daily Usage')).toBeVisible()
  })

  test('navigates back to highlights', async ({ page }) => {
    await page.goto('/stats')
    await page.click('a[href="/"]')
    await expect(page).toHaveURL('/')
    await expect(page.locator('h1', { hasText: 'Highlights' })).toBeVisible()
  })
})
