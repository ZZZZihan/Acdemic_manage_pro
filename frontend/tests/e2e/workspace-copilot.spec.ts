import { expect, test } from './authenticated-test'

test.describe('Workspace Copilot', () => {
  test('creates approval and task flow from real UI actions', async ({ page, request }) => {
    await page.goto('/workspace')

    await expect(page.getByTestId('workspace-title')).toBeVisible()
    const approvalCards = page.getByTestId('approval-card')
    const approvalCountBefore = await approvalCards.count()

    const created = page.waitForResponse(response => response.url().endsWith('/api/v2/chat/messages') && response.request().method() === 'POST')
    await page.getByTestId('send-message-button').click()
    const createdResponse = await created
    expect(createdResponse.ok()).toBeTruthy()
    const approval = (await createdResponse.json()).approval
    await expect(approvalCards).toHaveCount(approvalCountBefore + 1)

    await page.getByTestId('quick-action-task').click()
    const tasked = page.waitForResponse(response => response.url().endsWith('/api/v2/chat/messages') && response.request().method() === 'POST')
    await page.getByTestId('send-message-button').click()
    const taskResponse = await tasked
    expect(taskResponse.ok()).toBeTruthy()
    const task = (await taskResponse.json()).tool_calls.find(item => item.tool === 'task.create').result.task
    await expect(page.getByText('task.create')).toBeVisible()

    const newlyCreatedApprovalCard = page.locator(`[data-approval-id="${approval.id}"]`)
    const decided = page.waitForResponse(response => response.url().endsWith(`/api/v2/approvals/${approval.id}/decision`))
    await newlyCreatedApprovalCard.getByTestId('approval-approve-button').click()
    expect((await decided).ok()).toBeTruthy()
    await expect(newlyCreatedApprovalCard).toContainText('approved')
    const headers = { Authorization: `Bearer ${await page.evaluate(() => localStorage.getItem('token'))}` }
    const storedTask = await request.post('/mcp/resources/read', { headers, data: { uri: `lab://tasks/${task.id}` } })
    expect(storedTask.ok()).toBeTruthy()
    expect((await storedTask.json()).contents).toMatchObject({ id: task.id, source_thread_id: approval.thread_id })
    const storedApprovals = await request.get('/api/v2/approvals', { headers })
    expect(storedApprovals.ok()).toBeTruthy()
    expect((await storedApprovals.json()).items).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: approval.id, status: 'approved' }),
    ]))
  })
})
