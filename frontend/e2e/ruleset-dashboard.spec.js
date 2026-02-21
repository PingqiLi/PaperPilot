import { test, expect } from '@playwright/test'

let topicId

test.describe('Topic dashboard', () => {
  test.beforeEach(async ({ request }) => {
    const rsResp = await request.post('/api/v1/rulesets', {
      data: {
        name: `Dashboard Test ${Date.now()}`,
        topic_sentence: 'Testing the dashboard page with papers and filters',
        categories: ['cs.AI'],
        keywords_include: ['testing'],
        keywords_exclude: [],
        search_queries: ['dashboard testing'],
      },
    })
    const rs = await rsResp.json()
    topicId = rs.id
  })

  test('shows topic details', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await expect(page.locator('h1', { hasText: 'Dashboard Test' })).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Testing the dashboard page')).toBeVisible({ timeout: 5000 })
  })

  test('shows Initialize button when not initialized', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await expect(page.getByRole('button', { name: 'Initialize' }).first()).toBeVisible()
  })

  test('has Papers, Digests and Settings tabs', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await expect(page.locator('button', { hasText: 'Papers' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Digests' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Settings' })).toBeVisible()
  })

  test('papers tab shows empty state', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await expect(page.locator('text=Run Initialize to discover foundational papers')).toBeVisible()
  })

  test('settings tab shows categories and queries', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Settings")')
    await expect(page.locator('text=cs.AI')).toBeVisible()
    await expect(page.locator('text=dashboard testing')).toBeVisible()
  })

  test('filter buttons are visible', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await expect(page.locator('button', { hasText: 'All' }).first()).toBeVisible()
    await expect(page.locator('button', { hasText: 'Inbox' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Favorited' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Archived' })).toBeVisible()
  })

  test('back button navigates to highlights', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("All Topics")')
    await expect(page).toHaveURL('/')
  })

  test('digests tab shows generation buttons', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Digests")')
    await expect(page.locator('text=Field Overview')).toBeVisible()
    await expect(page.locator('text=Weekly Digest')).toBeVisible()
    await expect(page.locator('text=Monthly Report')).toBeVisible()
  })

  test('digests tab shows empty state', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Digests")')
    await expect(page.locator('text=No digests yet')).toBeVisible()
  })

  test('digests tab shows type descriptions', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Digests")')
    await expect(page.locator('text=Comprehensive overview of the research landscape')).toBeVisible()
    await expect(page.locator("text=Summary of this week's papers and trends")).toBeVisible()
    await expect(page.locator('text=Monthly analysis with clusters and momentum')).toBeVisible()
  })

  test('settings tab has edit button', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Settings")')
    await expect(page.locator('button', { hasText: 'Edit' })).toBeVisible()
  })

  test('settings edit mode shows form fields', async ({ page }) => {
    await page.goto(`/topics/${topicId}`)
    await page.click('button:has-text("Settings")')
    await page.click('button:has-text("Edit")')
    await expect(page.locator('text=Name')).toBeVisible()
    await expect(page.locator('text=Topic Sentence')).toBeVisible()
    await expect(page.locator('button', { hasText: 'Save Changes' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Cancel' })).toBeVisible()
  })
})
