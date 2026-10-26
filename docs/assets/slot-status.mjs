// A receipt describes a processing outcome, not the existence of a published article.
export function slotStatus(record, planned, clock, historical = false) {
  if (new Date(planned) > clock) return '未到执行时间';
  const status = record?.status;
  if (['already_published', 'no_matching_in_window', 'empty_digest'].includes(status)) return '今日无新增';
  if (status === 'insufficient_abstract') return '来源资料不足，本次未发布';
  const exhausted = historical || (record?.attempts || 0) >= 3;
  if (status === 'analysis_rejected') return exhausted ? '内容未通过检查，本次未发布' : '内容未通过检查，等待重试';
  if (['source_failure', 'analysis_api_failure'].includes(status)) return exhausted ? '执行异常，本次未发布' : '执行异常，等待重试';
  if (['prepared', 'published'].includes(status)) return historical ? '发布状态待核验' : '内容已生成，发布确认中';
  if (historical) return '本时段未发布（无可核验结果）';
  return clock - new Date(planned) > 20 * 60000 ? '执行延迟，等待补偿' : '等待任务结果';
}
