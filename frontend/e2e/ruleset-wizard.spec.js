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

test.describe('Topic wizard', () => {
  test('shows topic input step initially', async ({ page }) => {
    await page.goto('/topics/new')
    await expect(page.locator('h1', { hasText: 'New Topic' })).toBeVisible()
    await expect(page.locator('text=What are you researching?')).toBeVisible()
    await expect(page.locator('textarea')).toBeVisible()
  })

  test('generate button disabled when topic too short', async ({ page }) => {
    await page.goto('/topics/new')
    const btn = page.locator('button', { hasText: 'Generate Draft' })
    await expect(btn).toBeDisabled()

    await page.fill('textarea', 'short')
    await expect(btn).toBeDisabled()
  })

  test('generate button enabled when topic is long enough', async ({ page }) => {
    await page.goto('/topics/new')
    await page.fill('textarea', 'I am interested in efficient inference techniques for large language models')
    const btn = page.locator('button', { hasText: 'Generate Draft' })
    await expect(btn).toBeEnabled()
  })

  test('full wizard flow with mocked LLM draft', async ({ page, request }) => {
    await deleteAllRulesets(request)

    await page.route('**/api/v1/rulesets/draft', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          name: 'LLM Inference Optimization',
          topic_sentence: 'Efficient inference for large language models',
          categories: ['cs.AI', 'cs.LG'],
          keywords_include: ['quantization', 'pruning', 'KV-cache'],
          keywords_exclude: ['survey', 'benchmark'],
          search_queries: ['LLM inference optimization', 'neural network quantization methods'],
        }),
      })
    })

    await page.goto('/topics/new')

    await page.fill('textarea', 'Efficient inference for large language models')
    await page.click('button:has-text("Generate Draft")')

    await expect(page.locator('input[value="LLM Inference Optimization"]')).toBeVisible({ timeout: 5000 })

    await expect(page.locator('text=cs.AI')).toBeVisible()
    await expect(page.locator('text=cs.LG')).toBeVisible()
    await expect(page.getByText('quantization', { exact: true })).toBeVisible()
    await expect(page.getByText('pruning', { exact: true })).toBeVisible()

    await page.click('button:has-text("Create Topic")')

    await expect(page).toHaveURL(/\/topics\/\d+/, { timeout: 10000 })
    await expect(page.locator('h1', { hasText: 'LLM Inference Optimization' })).toBeVisible()
  })

  test('back button returns to previous page', async ({ page }) => {
    await page.goto('/')
    await page.locator('a[href="/topics/new"]').first().click()
    await expect(page).toHaveURL('/topics/new')

    await page.click('button:has-text("Back")')
    await expect(page).toHaveURL('/')
  })
})
