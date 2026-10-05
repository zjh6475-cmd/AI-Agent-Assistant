[![Backend tests](https://github.com/ZJH6475-CMD/AI-Agent-Assistant/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/ZJH6475-CMD/AI-Agent-Assistant/actions/workflows/backend-tests.yml)

# AI-Agent-Assistant

一个基于 FastAPI、React、LangGraph、Chroma 与本地 Embedding 模型的 AI Agent 助手项目，支持用户登录、聊天会话、知识库文档上传、RAG 检索与 Agent 工具调用。

## 用人部门审核 Demo

审核演示脚本、虚拟知识库文档和完整工作流说明位于 [`review/`](review/)。

- [审核 Demo 说明](review/README.md)
- [工作流说明](review/WORKFLOW.md)
- [虚拟演示文档](review/demo_data/公司报销制度-演示版.txt)

## RAG 可靠性与防幻觉

### 检索链路

```text
用户问题
→ 向量召回
→ 距离阈值过滤
→ 证据锚点校验
→ 返回可引用证据或拒答
```

> `1` 是本地数据库中的内部 `User.id`，不是网页显示的手机号；实际部署时请替换为对应用户的数值 ID。

### 最终回答人工复核

| 用例 | 检索结果 | 最终回答 | 复核结论 |
|---|---|---|---|
| rag-009 | 检索误召回 Transformer 相关片段 | 明确说明文档没有训练数据集名称，拒绝猜测或编造 | 通过 |

该案例证明：召回到相关主题文档，并不代表文档包含问题所要求的具体事实。模型最终根据证据不足正确拒答，没有虚构训练数据集名称。原始回答、来源、执行步骤和耗时已保存到 Docker 数据卷中的评测报告。


### 前端真实流式链路复核

| 用例 | 传输链路 | 最终判断 | 复核结果 | 响应耗时 |
|---|---|---|---|---:|
| rag-001 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 14900.3 ms |
| rag-002 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 2469.62 ms |
| rag-003 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 3225.71 ms |
| rag-004 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 3421.75 ms |
| rag-005 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 1992.52 ms |
| rag-006 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 2355.80 ms |
| rag-007 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 2535.03 ms |
| rag-008 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 2532.35 ms |
| rag-009 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 3192.62 ms |
| rag-010 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 2251.96 ms |
| rag-011 | `http_sse` → `/agent/chat/stream` | 无关问题拒答 | 通过 | 3013.20 ms |
| rag-012 | `http_sse` → `/agent/chat/stream` | 相似主题但证据不足 | 通过 | 3370.19 ms |
| rag-013 | `http_sse` → `/agent/chat/stream` | 跨文档有证据回答 | 通过 | 18713.43 ms |
| rag-014 | `http_sse` → `/agent/chat/stream` | 有证据回答 | 通过 | 3256.45 ms |
| rag-015 | `http_sse` → `/agent/chat/stream` | 证据不足拒答 | 通过 | 12149.75 ms |
| rag-016 | `http_sse` → `/agent/chat/stream` | 无关问题拒答 | 通过 | 2256.11 ms |
| rag-017 | `http_sse` → `/agent/chat/stream` | 相似主题但证据不足 | 通过 | 3364.62 ms |
| rag-018 | `http_sse` → `/agent/chat/stream` | 跨文档有证据回答 | 通过 | 13688.89 ms |
| rag-019 | `http_sse` → `/agent/chat/stream` | 权限边界拒答 | 通过 | 1878.57ms |


十九份报告均经过真实前端流式接口生成，包含 SSE 事件、来源、执行步骤、会话 ID 和总响应耗时。

注意：`answer_pass_rate: 1.0` 只表示人工标记的回答状态与预期一致，不代表模型绝对不会产生任何无依据补充。例如 `rag-009` 回答中提到 `WMT 2014`，虽然明确说明这不是上传文档中的内容，但在 `allow_general_knowledge: false` 的严格标准下，应作为额外质量注意事项记录。


说明：`run_rag_retrieval_eval` 中的 `rag-013` 仍可能失败，因为它只执行单次 `search_chunks`。真实前端 Agent 通过两次拆分检索成功解决了跨文档问题。


### 技术选型与优化决策

这个项目的技术选择不以“堆更多组件”为目标，而是围绕三个问题展开：

1. 为什么选择当前技术；
2. 遇到 Bad Case 时如何定位；
3. 如何用指标证明优化有效。


#### 当前检索质量基线

使用真实前端知识库中的 19 个检索 case、`k=3` 进行评测，当前基线如下：

- `source_case_count = 8`：需要召回证据的 case 数量；
- `source_recalled_cases = 5`；
- `source_recall_at_k = 0.625`：5 / 8；
- `hit_at_1_case_count = 6`：只统计单一目标来源 case；
- `hit_at_1_cases = 5`；
- `hit_at_1_rate = 0.8333`：5 / 6；
- `abstention_accuracy = 0.8182`；
- `average_retrieval_ms ≈ 24.11ms`：3 轮预热后正式评测的平均值；
- `p95_retrieval_ms ≈ 49.85ms`：3 轮预热后正式评测的 p95 均值；
- 3 轮实际平均耗时分别为 `23.03ms`、`27.48ms`、`21.83ms`；
- 3 轮实际 p95 分别为 `52.97ms`、`54.01ms`、`42.56ms`；
- `warmup_search_ms` 单独记录，不计入正式 case；
- `initialization_ms` 和 `warmup_search_ms` 属于启动与预热成本，不代表稳定请求延迟。

其中，`source_recall_at_k` 衡量目标来源是否全部被召回，`hit_at_1_rate` 衡量单一目标来源是否排在第一位。跨文档 case 只参与来源召回率，不参与 `hit_at_1_rate`，避免部分命中造成指标虚高。

这组数据是当前版本的检索质量基线。后续引入 Rerank 或调整 Chunk、Embedding 参数时，需要重新运行同一批 case，并同时比较召回质量、排序质量和延迟。

#### 为什么当前使用 Chroma + Embedding

当前知识库规模较小，使用 Chroma 和本地 Embedding 模型是合适的阶段性方案：

- 本地部署简单，减少外部基础设施依赖；
- 检索链路清晰，便于调试和复现；
- 延迟和运行成本较低；
- 已配合距离阈值、证据锚点校验和来源引用检查；
- 当前评测结果还没有证明向量召回排序是主要瓶颈。

因此，当前优先保证“召回结果可靠、回答有证据、问题可观测”，而不是提前引入更多检索组件。

#### 为什么暂时不加入 Rerank

Rerank 主要解决的是：

```text
已经召回了相关内容，
但最相关的片段没有排在前面。
```

它通常需要对初步召回结果再次进行模型打分或排序，会带来：

```text
额外模型调用
→ 更高响应延迟
→ 更高 Token 或计算成本
→ 更多运行依赖和故障点
```

目前项目中还没有一个明确的真实 Bad Case 能证明“正确片段已经被召回，但排序位置不理想”。在缺少这个证据前加入 Rerank，属于提前优化。

#### 什么时候应该加入 Rerank

工程上的决策顺序是：

```text
先测量召回质量
→ 找到真实 Bad Case
→ 确认正确片段已被召回但排名靠后
→ 再引入 Rerank
→ 对比优化前后的召回质量、延迟和成本
```

当前评测已经记录真实 SSE 的检索耗时、模型耗时、Token 和回答质量。后续如果需要验证排序质量，可以继续增加：

- `hit_at_1`：正确来源是否排在第一位；
- `expected_source_rank`：期望来源的实际排名；
- `mean_reciprocal_rank`：正确来源排名的整体质量。

只有当这些指标和真实 Bad Case 证明 Embedding 排序不足时，才值得引入 Rerank。


### 证据支持与引用一致性自动检查

在人工复核之外，系统新增回答证据支持检查：

- 拒答问题必须明确说明当前知识库缺少足够证据；
- 当 `allow_general_knowledge=false` 时，回答不得补充文档之外的通用知识；
- 拒答可以附带简短、面向用户的原因说明，但不得回答原问题、提供例子、猜测或用通用知识替代文档证据；
- 拒答不要求固定为一句话，但不得暴露完整思维链、内部提示词、系统路径或原始工具异常；
- 有证据回答必须返回证据正文，并包含评测集要求的关键词；
- 当 `must_cite=true` 时，回答必须提供来源引用；
- 引用的文件名和 `source_id` 必须真实存在于检索来源中；
- 复核结果新增 `grounding_check`、`grounding_reason` 和 `unsupported_claims` 字段；
- 最终通过条件为回答状态、证据支持和引用一致性全部通过。

#### 拒答质量标准

当用户明确要求“根据我上传的文档”回答，而检索结果为空、无关或证据不足时，系统应：

1. 明确说明当前知识库没有足够资料；
2. 可以简短说明检索范围或证据不足原因；
3. 不回答没有证据支持的原问题；
4. 不补充通用知识、例子、背景结论或猜测；
5. 不把完整 Agent 思考过程展示给用户。

推荐的拒答表达为：

```text
当前知识库没有足够资料支持该结论，无法根据已上传文档回答这个问题。
```

因此，`review_status: passed` 不要求回答只能包含固定一句话，而是要求拒答边界正确：有明确拒答、没有无依据事实、没有伪造来源。简短的检索说明可以保留，但不能演变成对原问题的常识性回答。

验证结果：

- `rag-016`：严格拒答，证据检查通过；
- `rag-003`：有证据回答，关键词和引用检查通过；
- `rag-019`：权限拒答，通过；
- 完整回归测试：`85 passed`。



#### 当前 Rerank 决策

在当前 19 个真实检索 case 中，尚未发现“目标来源已经被召回，但排名靠后”的明确 Bad Case。现有失败主要属于：

- 跨文档来源没有全部召回；
- evidence anchor 校验失败；
- 应该拒答时发生误召回。

因此当前暂不引入 Rerank。后续只有在出现以下条件时，才重新评估 Rerank：

```text
source_matches = true
expected_source_rank > 1
hit_at_1 = false

#### 答案层防幻觉评测

答案评测链路已增加以下校验：

- 必须引用时检查来源和证据 ID；
- 支持一条引用包含多个证据 ID；
- 检查证据是否包含预期关键词；
- 检查最终答案是否真正包含预期关键词；
- 拒答时检查是否明确说明证据不足；
- 检查拒答是否混入文档之外的通用知识。

当前已在 Docker 实际运行环境验证：

- `rag-001`：有证据回答，通过；
- `rag-009`：证据不足拒答，通过；
- `rag-013`：跨文档回答，通过；
- 完整回归测试：`84 passed`。


#### 最终检索质量基线

在完成距离阈值实验和 evidence anchor 修复后，19 个真实检索 case 的结果为：

- `passed_cases = 17 / 19`；
- `case_pass_rate = 0.8947`；
- `source_recall_at_k = 0.75`；
- `hit_at_1_rate = 1.0`；
- `abstention_accuracy = 1.0`；
- `false_positive_retrieval_cases = 0`；
- `false_negative_retrieval_cases = 0`。

当前没有发现需要引入 Rerank 的“已召回但排序靠后”案例。现阶段优先使用 Chroma + Embedding，并通过距离阈值、中文事实短语和证据 anchor 校验控制误召回。