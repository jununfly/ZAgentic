// mock 服务端的确定性结果定义。
// OUTCOME 描述一次持久化调用可能得到的三类结局：成功 / 服务端约束拒绝 / 超时。

export const OUTCOME = {
  OK: 'ok',
  CONFLICT: 'conflict',
  TIMEOUT: 'timeout'
};

// 稳定路径：当服务端结局不可判定（超时）时，流程回退到的确定性路径。
// 回退只保留最后已知良好的本地草稿，并对外显式标记「结果未确认」，绝不伪造成功。
export const STABLE_PATH = 'stable_path';

export function outcomeFromResponseCode(code, error) {
  if (code === 200) return OUTCOME.OK;
  if (code === 0 || error === 'timeout') return OUTCOME.TIMEOUT;
  return OUTCOME.CONFLICT;
}

export function isUnresolvedOutcome(error) {
  return error === 'timeout';
}
