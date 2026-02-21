import { test, expect } from '@playwright/test'

async function deleteAllRulesets(request) {
  const resp = await request.get('/api/v1/rulesets')
  if (resp.ok()) {
    const rulesets = await resp.json()
    for (const rs of rulesets) {
      await request.delete(`/api/v1/rulesets/${rs.id}`)
    }
  }
}

test.describe('Papers highlights page', () => {
  test.describe('empty state', () => {
    test.beforeEach(async ({ request }) => {
      await deleteAllRulesets(request)
    })

    test('shows empty state when no highlights', async ({ page }) => {
      await page.goto('/')
      await expect(page.locator('text=No highlights yet')).toBeVisible()
      await expect(page.locator('text=Create a topic to discover high-scoring papers')).toBeVisible()
    })
  })

  test('shows page heading and description', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('h1', { hasText: 'Highlights' })).toBeVisible()
    await expect(page.locator('text=Top-scored papers across all topics')).toBeVisible()
  })

  test('has status filter buttons', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('button', { hasText: 'Highlights' }).first()).toBeVisible()
    await expect(page.locator('button', { hasText: 'All' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Favorites' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Archived' })).toBeVisible()
  })

  test('has sort dropdown', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('select')).toBeVisible()
  })

  test('favorites filter shows empty state', async ({ page, request }) => {
    await deleteAllRulesets(request)
    await page.goto('/')
    await page.click('button:has-text("Favorites")')
    await expect(page.locator('text=No favorites yet')).toBeVisible()
  })

  test('topic shows in sidebar after creating via API', async ({ page, request }) => {
    await deleteAllRulesets(request)
    const resp = await page.request.post('/api/v1/rulesets', {
      data: {
        name: `Test Topic ${Date.now()}`,
        topic_sentence: 'Machine learning for code generation and program synthesis',
        categories: ['cs.AI', 'cs.SE'],
        keywords_include: ['code generation', 'program synthesis'],
        keywords_exclude: ['survey'],
        search_queries: ['LLM code generation'],
      },
    })
    expect(resp.ok()).toBeTruthy()
    const rs = await resp.json()

    await page.goto('/')
    // Topic should appear in the sidebar Topics section
    await expect(page.locator(`a[href="/topics/${rs.id}"]`)).toBeVisible()
  })

  test('clicking topic in sidebar navigates to dashboard', async ({ page, request }) => {
    await deleteAllRulesets(request)
    const resp = await page.request.post('/api/v1/rulesets', {
      data: {
        name: `Navigate Test ${Date.now()}`,
        topic_sentence: 'Testing navigation to dashboard works correctly',
        categories: [],
        keywords_include: [],
        keywords_exclude: [],
        search_queries: [],
      },
    })
    const rs = await resp.json()

    await page.goto('/')
    await page.click(`a[href="/topics/${rs.id}"]`)
    await expect(page).toHaveURL(`/topics/${rs.id}`)
    await expect(page.locator('h1', { hasText: 'Navigate Test' })).toBeVisible()
  })
})
