# P12 行为包学习审核与回滚

## 审核边界

行为包学习引擎只生成候选包和建议，不自动启用任何候选包。所有候选包默认状态为 `pending_review`，需要人工审核后才能进入后续启用流程。

## 审核记录

审核动作写入 `behavior_learning/{app_id}/{run_id}/review_record.jsonl`，每行一个 JSON，至少记录：

- candidate_pack_id
- decision
- status
- reviewer
- note
- timestamp

允许的人工决策包括：

- approve：候选包进入 `approved`，可被后续显式启用流程使用。
- reject：候选包进入 `rejected`，不得启用。

## 回滚记录

回滚动作写入 `behavior_learning/{app_id}/{run_id}/rollback_record.jsonl`，每行一个 JSON，至少记录：

- candidate_pack_id
- rollback_target
- reviewer
- note
- timestamp

回滚只记录目标版本，不修改原始 run 产物，也不自动覆盖线上行为包。

## 禁止事项

- 不自动启用 `pending_review` 候选包。
- 不启用 `rejected` 候选包。
- 不修改历史 `summary.json`、`meta.jsonl`、`run.log`、`behavior_actions.jsonl`。
- 不训练模型，不下载模型，不执行真实采集动作。
