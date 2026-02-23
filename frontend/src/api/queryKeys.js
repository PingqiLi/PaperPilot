export const qk = {
  topicOverview: ['topicOverview'],
  rulesets: ['rulesets'],
  ruleset: (id) => ['ruleset', id],
  rulesetPapers: (id, ...rest) => ['rulesetPapers', id, ...rest],
  run: (rulesetId, runId) => ['run', rulesetId, runId],
  digests: (id) => ['digests', id],
  paperDetail: (rulesetId, paperId) => ['paperDetail', rulesetId, paperId],
  globalPapers: (...rest) => ['globalPapers', ...rest],
  activeTasks: ['activeTasks'],
  allTasks: ['allTasks'],
  draftTask: (taskId) => ['draftTask', taskId],
  settings: ['settings'],
  costStats: ['costStats'],
  dailyCosts: (days) => ['dailyCosts', days],
  requestHistory: (days, page) => ['requestHistory', days, page],
  emailLogs: ['emailLogs'],
  paperSearch: (rulesetId, q) => ['paperSearch', rulesetId, q],
}

export const invalidate = {
  rulesetChanged(queryClient, id) {
    queryClient.invalidateQueries({ queryKey: qk.ruleset(id) })
    queryClient.invalidateQueries({ queryKey: qk.topicOverview })
    queryClient.invalidateQueries({ queryKey: qk.rulesets })
  },

  rulesetDeleted(queryClient, id) {
    queryClient.removeQueries({ queryKey: qk.ruleset(id) })
    queryClient.invalidateQueries({ queryKey: qk.topicOverview })
    queryClient.invalidateQueries({ queryKey: qk.rulesets })
  },

  rulesetPapersChanged(queryClient, id) {
    queryClient.invalidateQueries({ queryKey: qk.rulesetPapers(id) })
    queryClient.invalidateQueries({ queryKey: qk.globalPapers() })
  },

  paperStatusChanged(queryClient, rulesetId, paperId) {
    if (paperId) {
      queryClient.invalidateQueries({ queryKey: qk.paperDetail(rulesetId, paperId) })
    }
    queryClient.invalidateQueries({ queryKey: qk.rulesetPapers(rulesetId) })
    queryClient.invalidateQueries({ queryKey: qk.globalPapers() })
  },

  runCompleted(queryClient, id) {
    queryClient.invalidateQueries({ queryKey: qk.ruleset(id) })
    queryClient.invalidateQueries({ queryKey: qk.rulesetPapers(id) })
    queryClient.invalidateQueries({ queryKey: qk.topicOverview })
  },

  topicCreated(queryClient) {
    queryClient.invalidateQueries({ queryKey: qk.rulesets })
    queryClient.invalidateQueries({ queryKey: qk.topicOverview })
    queryClient.invalidateQueries({ queryKey: qk.activeTasks })
    queryClient.invalidateQueries({ queryKey: qk.allTasks })
  },

  tasksChanged(queryClient) {
    queryClient.invalidateQueries({ queryKey: qk.activeTasks })
    queryClient.invalidateQueries({ queryKey: qk.allTasks })
  },

  settingsChanged(queryClient) {
    queryClient.invalidateQueries({ queryKey: qk.settings })
    queryClient.invalidateQueries({ queryKey: qk.costStats })
  },
}
