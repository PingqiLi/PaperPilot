import { test, expect } from '@playwright/test'

test.describe('App shell', () => {
  test('loads and shows sidebar with branding', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('text=Paper Agent')).toBeVisible()
    await expect(page.locator('text=v1.0')).toBeVisible()
  })

  test('sidebar has navigation links', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('a[href="/"]', { hasText: 'Highlights' })).toBeVisible()
    await expect(page.locator('a[href="/stats"]', { hasText: 'Cost Stats' })).toBeVisible()
  })

  test('sidebar has New Topic button', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('a[href="/topics/new"]', { hasText: 'New Topic' })).toBeVisible()
  })

  test('sidebar has collapsible Topics section', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('aside button', { hasText: 'Topics' })).toBeVisible({ timeout: 10000 })
  })

  test('navigates to cost stats page', async ({ page }) => {
    await page.goto('/')
    await page.click('a[href="/stats"]')
    await expect(page).toHaveURL('/stats')
    await expect(page.locator('h1', { hasText: 'Cost Stats' })).toBeVisible()
  })

  test('navigates to new topic page', async ({ page }) => {
    await page.goto('/')
    await page.locator('a[href="/topics/new"]').first().click()
    await expect(page).toHaveURL('/topics/new')
    await expect(page.locator('h1', { hasText: 'New Topic' })).toBeVisible()
  })

  test('root shows highlights landing page', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1', { hasText: 'Highlights' })).toBeVisible()
  })

  test('root API returns rulesets', async ({ page }) => {
    const resp = await page.request.get('/api/v1/rulesets')
    expect(resp.ok()).toBeTruthy()
  })
})

test.describe('Theme toggle', () => {
  test('sets data-theme attribute on load', async ({ page }) => {
    await page.goto('/')
    const theme = await page.locator('html').getAttribute('data-theme')
    // Theme is set based on system preference or localStorage
    expect(theme === 'dark' || theme === 'light').toBeTruthy()
  })

  test('toggles theme and back', async ({ page }) => {
    await page.goto('/')

    const initialTheme = await page.locator('html').getAttribute('data-theme')
    const otherTheme = initialTheme === 'dark' ? 'light' : 'dark'

    // Find and click theme toggle button (last button in sidebar)
    const toggleBtn = page.locator('aside button').last()
    await toggleBtn.click()

    const toggledTheme = await page.locator('html').getAttribute('data-theme')
    expect(toggledTheme).toBe(otherTheme)

    // Toggle back
    await toggleBtn.click()
    const restoredTheme = await page.locator('html').getAttribute('data-theme')
    expect(restoredTheme).toBe(initialTheme)
  })

  test('persists theme in localStorage', async ({ page }) => {
    await page.goto('/')
    const initialTheme = await page.locator('html').getAttribute('data-theme')
    const toggleBtn = page.locator('aside button').last()
    await toggleBtn.click()

    const expected = initialTheme === 'dark' ? 'light' : 'dark'
    const stored = await page.evaluate(() => localStorage.getItem('theme'))
    expect(stored).toBe(expected)
  })
})
