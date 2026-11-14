# 一手资料与证据边界

核对日期：2026-11-14。资料是设计依据与公开报价快照，不是本产品已实现、已验证或已获组织授权的证明。本仓库使用通用设计和合成案例，不复制私人对话、内部记录或第三方长篇原文。

引用范围分为：公开概念、技术机制、价格快照、研究报告。推荐方案与组织政策应在设计文档中另外标明，不能借引用替代决策。

## 概念与学习证据

### SRC-CONCEPT-LI

- [李彦宏演讲整理：AI 不止是一场技术革命，更是一场组织革命](https://finance.sina.com.cn/hy/hyjz/2026-11-12/doc-iniymwrc1218403.shtml)，2026-11-12。
- 支持范围：打破岗位边界、沉淀隐性知识、设计流程闭环等演讲主张。
- 边界：现场速记未经演讲者审阅，存在识别错误；不能据此证明本产品有效，也不能把演讲中的未来预测当成事实。

### SRC-CONCEPT-BAIDU

- [百度官方供稿：智能组织与全栈 AI 发布](https://www.prnewswire.com/news-releases/baidu-unveils-latest-ernie-models-amid-broader-full-stack-ai-lineup-and-debuts-token-exchange-to-power-intelligent-organizations-302937959.html)，2026-11-12。
- 支持范围：公司公布的组织原则、产品与内部使用指标。
- 边界：公司自述；智能体、任务或 Skill 数量不能独立证明净生产率、利润或 ROI 改善。

### SRC-BEHAVIOR-SYCOPHANCY

- [OpenAI：Expanding on what we missed with sycophancy](https://openai.com/index/expanding-on-sycophancy/)，2025-05-02。
- 支持范围：一次模型更新中，用户偏好反馈可能强化顺从行为，部分离线与 A/B 结果未捕捉到问题。
- 边界：具体版本事故的官方复盘，不能据此推断所有当前模型的表现；支持将“用户喜欢”与“判断可靠、问题解决”分开验证。

### SRC-RESEARCH-ALPHAEVOLVE

- [AlphaEvolve 一手论文](https://arxiv.org/abs/2506.13131)，2025-06-16。
- [DeepMind 官方介绍与部署报告](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)，2025-05-14。
- 支持范围：生成候选程序、使用评估器检验、选择与改进算法；研究团队报告了数学及计算基础设施结果。
- 边界：可验证算法任务的研究与开发者报告。候选程序持续改进不等于底层模型每轮自动更新权重，也不能直接证明开放组织判断的可靠性。

### SRC-ENGINEERING-LOOP

- [OpenAI Cookbook：Build an Agent Improvement Loop with Traces, Evals, and Codex](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)，页面日期 2026-05-12。
- 支持范围：将执行记录、反馈、评测与 harness 改进连接起来的示例。
- 边界：教程使用合成公司材料；示例存在不能证明 OrgLoop 的新情境迁移、真实 ROI 或部署成熟度。

## 架构与工程机制

### SRC-PG-RLS

- [PostgreSQL 18：Row Security Policies](https://www.postgresql.org/docs/18/ddl-rowsecurity.html)。
- 支持范围：按策略约束行级读取与修改。
- 边界：超级用户、具备 BYPASSRLS 的角色及默认表所有者存在绕过条件；RLS 不能代替应用授权、工具授权或所有数据泄露防护。实现必须明确连接角色并测试隔离。

### SRC-PG-SELECT

- [PostgreSQL 18：SELECT](https://www.postgresql.org/docs/18/sql-select.html)。
- 支持范围：事务内行锁和 SKIP LOCKED 等查询机制，可作为任务争抢的实现基础。
- 边界：行锁不自动提供外部 API 的恰好一次执行。任务租约、幂等、回执核实和崩溃恢复仍需设计与测试；SKIP LOCKED 适用性不能扩展为一般查询一致性保证。

### SRC-FASTAPI-BACKGROUND

- [FastAPI：Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)。
- 支持范围：响应后执行的应用后台任务，以及重型任务使用独立工具的说明。
- 边界：框架后台任务不能直接充当可恢复的持久工作流；长期事项必须由持久状态和 worker 管理。

### SRC-VITE

- [Vite：Getting Started](https://vite.dev/guide/)。
- 支持范围：独立前端开发服务器和构建工具。
- 边界：构建工具不提供后端身份、数据库授权或集成密钥保护。前后端分离仍需版本化 API、部署与权限边界。

### SRC-OPENAPI

- [OpenAPI Specification 3.1.1](https://spec.openapis.org/oas/v3.1.1.html)，2024-10-24。
- 支持范围：机器可读 API 契约、路径、操作、schema 与安全声明。
- 边界：文档采用的契约版本，不宣称是最新版本；静态契约有效不能证明后端实现、授权或运行行为正确。

### SRC-PGVECTOR

- [pgvector 官方仓库](https://github.com/pgvector/pgvector)。
- 支持范围：PostgreSQL 内的向量存储与相似度检索、索引机制。
- 边界：相似度不证明真实性、适用性或人员能力。过滤、召回、索引配置与权限组合需要独立验证。

### SRC-TEMPORAL

- [Temporal：Workflow Execution overview](https://docs.temporal.io/workflow-execution)。
- 支持范围：持久执行、工作流生命周期与恢复机制的参考。
- 边界：作为后续复杂工作流方案的比较依据，不代表首版必须引入 Temporal；采用它也不会免除外部副作用幂等和业务授权责任。

## 价格与账单

以下来源与 [COSTS.md](COSTS.md)、[rates.json](../pricing/rates.json)、[scenarios.json](../pricing/scenarios.json) 对应。报价可能按地区、模式、账户与日期变化，正式采购前重核。

### SRC-PRICE-OPENAI

- [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)。
- 支持范围：按模型和处理模式列出的 token 与工具价格。
- 边界：算例使用指定短上下文 Standard 档，未包含账户限制、税费、缓存写入、长上下文、地区附加费或所有工具。

### SRC-PRICE-LUNA

- [GPT-6 Luna 模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)。
- 支持范围：Standard 短上下文每百万输入／输出 0.10／0.50 USD、缓存与长上下文等计费说明。
- 边界：价格与官方功能描述不能证明模型在组织任务上达标。

### SRC-PRICE-SOL

- [GPT-6.1 Sol 模型页](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。
- 支持范围：Standard 短上下文每百万输入／输出 2.00／10.00 USD、缓存与模式附加说明。
- 边界：工具协议和能力必须通过本产品适配与场景验证；未依照旧版本或订阅价格推算 API 费用。

### SRC-PRICE-EMBEDDING

- [text-embedding-3-small 模型页](https://developers.openai.com/api/docs/models/text-embedding-3-small)。
- 支持范围：每百万输入 tokens 0.02 USD 的向量化报价。
- 边界：不包含 OCR、解析、向量索引、存储、重建和维护。

### SRC-PRICE-DEEPSEEK

- [DeepSeek：Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/)。
- 支持范围：Flash、Pro 的峰谷及缓存价格，以及公开工具计价。
- 边界：本预算采用峰时未缓存价，不能保证实际任务的质量、时延或用量与另一模型相同。模型别名可能升级，实施需记录实际模型版本。

### SRC-BILLING-REASONING

- [OpenAI：Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)。
- 支持范围：推理 tokens 参与计费输出与上下文的说明。
- 边界：预算以供应商实际 usage 对账，不能从可见回答字数推断总成本。

### SRC-BILLING-DEEPSEEK

- [DeepSeek：Using the Responses API](https://api-docs.deepseek.com/guides/responses_api/)。
- 支持范围：usage 中 input_tokens、output_tokens 和推理输出明细。
- 边界：原始 usage 与归一化字段都应保留，不能把不同协议名称简单视为完全兼容。

### SRC-PRICE-AWS

- [Amazon Lightsail Pricing](https://aws.amazon.com/lightsail/pricing/)。
- 支持范围：公开 Linux IPv4 VM 资源包、按实际保留量计费的快照价格。
- 边界：参考价不是本组织所在地区的合同报价；包内流量和地区条件需核对，单机价格不证明生产容量或高可用。

### SRC-PRICE-SUPABASE

- [Supabase Pricing](https://supabase.com/pricing)。
- 支持范围：Pro 订阅、计算额度与 Large 计算价格、备份与 PITR 附加项。
- 边界：25 USD 起价只覆盖基础配置；同一订阅额度仅抵扣一次。托管不自动满足组织的隔离、RPO、RTO 和区域要求。

### SRC-PRICE-R2

- [Cloudflare R2 Pricing](https://developers.cloudflare.com/r2/pricing/)。
- 支持范围：Standard 对象 GB月、操作与免费量的报价。
- 边界：免费量按账户月度汇总，不可在每个 bucket 重复扣除；直接出网免费不覆盖其他关联服务费用。对象持久性也不等于完整应用恢复证明。

## 更新约定

1. 记录核对日期、原链接、适用版本与引用边界，修改价格时同步结构化价格快照和算例。
2. 官方资料之间发生冲突时保留冲突，优先使用当前具体模型／服务页面并重新核实，不用搜索摘要掩盖差异。
3. 外部来源失效或价格改变时，旧记录保留为历史快照；不能继续用旧结果为新版本背书。
4. 文档、算术复核、契约检查、运行测试和组织效果验证分别报告。
