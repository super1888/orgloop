# API 与前后端契约

状态：OpenAPI 3.1.1 设计契约，尚无后端实现。机器可读定义以 [openapi.json](../contracts/openapi.json) 为准；[示例](../contracts/examples.json)用于静态结构验证，不是成功调用记录。下表覆盖目标设计，各能力按[开发顺序](DEVELOPMENT.md)和[路线](ROADMAP.md)交付，不要求第一阶段同时实现全部接口。

## 1. 通信和身份

- `/v1` REST JSON API，时间使用带时区的 RFC3339，资源标识使用 UUID，`version` 为正整数。
- 前端独立构建，默认经同源反向代理访问 API；Cookie 为后端安全会话，生产使用 HttpOnly、Secure、合适的 SameSite。前端不保存模型、数据库或业务系统密钥。
- OIDC 登录由后端处理：站内返回路径白名单，校验 state/nonce/PKCE/issuer/audience；回调 code、Cookie、令牌不写普通日志。登录/回调无需已有会话，其余接口必须认证。
- `/v1/session` 返回当前成员、组织与 CSRF 令牌。写入及 POST 检索要求会话绑定的 `X-CSRF-Token`，同时检查来源；组织切换根据 `membership_id` 核验，重建会话上下文。
- 调用主体及组织由后端确定。业务写入不接受任意 `organization_id` 或 `acting_as`。授权书的 `delegatee_id` 是被授权对象，仍须由后端核实，不改变实际调用身份。
- 每次查询、附件、事件、摘要、历史引用和幂等重放均按当前权限重新过滤。无权发现的资源不能通过错误、计数或“后台存在”提示泄漏。
- 对话/来源中的内容不能授予权限。模型输出先验结构、引用、对象存在性及当前授权，再转换为领域命令。

## 2. 并发、幂等与异步

| 机制 | 契约 |
|---|---|
| 聚合并发 | GET 返回强 ETag，例如 `"3"`；契约声明的修改携带 `If-Match`。缺少返回428，版本陈旧返回412；刷新并重新理解差异，不静默覆盖。 |
| 命令幂等 | 新增和命令使用 `Idempotency-Key`。作用域含组织、实际主体与操作；同键同负载返回原始资源/结果，同键异负载409。POST只读检索不使用命令重放缓存。 |
| 授权绑定 | 后端生成动作负载摘要；授权绑定 `action_id/proposal_version/payload_digest`、被授权人、决定、条件、期限与预算。参数或必要条件变化后重新判断授权。 |
| 可靠接收 | 202表示任务与必要事件已持久记录；使用Location或返回的run/job读取进度，不表示外部效果已成功。 |
| 未知外部结果 | 超时不自动记失败；无法查证时 `outcome_unknown`，核实后才决定下一步。没有幂等/核实能力的连接器禁止盲重试。 |
| 取消 | 停止后续可停止步骤；在途及未知结果继续核实。取消响应不许诺撤销已经产生的效果。 |
| 事件 | JSON游标分页，只返回当前有权看到的事件；首版按需刷新，活动事项可有限退避轮询，窗口不可见时暂停。无需SSE/WebSocket。 |

幂等记录与负载摘要应关联实际命令和外部尝试，不按短缓存过期就重新执行。未决动作及业务重试窗口内必须保留；按POL-008归档时保留必要去重凭据。重放前重新检查身份与可见性，不能返回旧权限下缓存的原文。新的资源权限不通过幂等键获得。

Action的`proposal_version`标识不可变提案内容，`version`/ETag用于生命周期并发。正常ready/executing/outcome_unknown变化不改变内容摘要；改变执行内容建立新提案并重新授权。

动作摘要覆盖连接器、工具名、目标、规范化参数、执行模式和必要来源版本。采用经测试的规范化序列化后计算SHA-256；调用者读取服务端摘要，不能以自行构造的摘要替换。`max_cost_usd` 是模型/工具预算；资金、库存、工时和现场操作的约束还需工具专用schema及组织政策验证，未实现验证的写能力保持禁用。

## 3. 接口目录

| 方法 | 路径 | 用途 | 需求 |
|---|---|---|---|
| `GET` | `/v1/session` | 读取会话、组织与CSRF令牌 | REQ-014 |
| `POST` | `/v1/auth/logout` | 撤销当前会话并清理Cookie | REQ-014 |
| `POST` | `/v1/session/organization-switches` | 核实成员资格后切换组织并重建会话上下文 | REQ-014 |
| `GET` | `/v1/work-items` | 列出当前可见事项 | REQ-001 |
| `POST` | `/v1/work-items` | 发起事项并建立持续工作空间 | REQ-001 |
| `GET` | `/v1/work-items/{id}` | 读取事项快照 | REQ-001 |
| `PATCH` | `/v1/work-items/{id}` | 修改目标与约束，保留修订 | REQ-001 |
| `POST` | `/v1/work-items/{id}/transitions` | 根据证据与权限改变运行状态 | REQ-001, REQ-007 |
| `GET` | `/v1/work-items/{id}/events` | 读取当前可见的游标事件 | REQ-001, REQ-013, REQ-014 |
| `POST` | `/v1/work-items/{id}/runs` | 启动有预算和步数边界的调查或推进 | REQ-001, REQ-005, REQ-014 |
| `GET` | `/v1/runs/{id}` | 读取Agent运行状态 | REQ-006 |
| `POST` | `/v1/runs/{id}/commands` | 请求暂停、继续或取消，保留已发生动作 | REQ-006 |
| `POST` | `/v1/context/search` | 按事项权限检索有来源和版本的上下文 | REQ-002 |
| `POST` | `/v1/sources` | 创建已获准共享的文本来源，异步建立索引 | REQ-002, REQ-011 |
| `GET` | `/v1/sources/{id}` | 读取可见来源元数据 | REQ-002 |
| `POST` | `/v1/sources/{id}/corrections` | 提交来源纠错，原始版本保留 | REQ-007, REQ-011 |
| `POST` | `/v1/sources/{id}/access-revocations` | 先阻断授权范围内的派生读取，再清理索引 | REQ-002, REQ-011, REQ-014 |
| `POST` | `/v1/resources/search` | 查找允许发现的能力、关系和资源线索 | REQ-003 |
| `POST` | `/v1/capability-offers` | 提交具体任务能力与共享范围 | REQ-003, REQ-011 |
| `POST` | `/v1/work-items/{id}/support-requests` | 申请具体支持，尚不构成承诺 | REQ-004 |
| `GET` | `/v1/support-requests/{id}` | 读取支持请求与承接情况 | REQ-004 |
| `POST` | `/v1/support-requests/{id}/responses` | 由有权者接受、补条件、拒绝或撤回 | REQ-004 |
| `POST` | `/v1/support-requests/{id}/fulfilments` | 记录实际帮助与证据 | REQ-004, REQ-007 |
| `POST` | `/v1/work-items/{id}/decisions` | 由有权的人记录取舍和剩余风险 | REQ-005 |
| `POST` | `/v1/authorizations` | 对明确动作授予有限委托 | REQ-005 |
| `GET` | `/v1/authorizations/{id}` | 读取有效授权 | REQ-005 |
| `POST` | `/v1/authorizations/{id}/revocations` | 撤回后续执行权限 | REQ-005 |
| `POST` | `/v1/work-items/{id}/actions` | 创建工具动作建议，默认不获得执行权 | REQ-005, REQ-006 |
| `GET` | `/v1/actions/{id}` | 读取动作状态与回执关联 | REQ-006 |
| `POST` | `/v1/actions/{id}/executions` | 校验授权后入队执行或模拟 | REQ-005, REQ-006 |
| `POST` | `/v1/actions/{id}/reconciliations` | 核实未知外部结果，禁止盲重试 | REQ-006 |
| `POST` | `/v1/work-items/{id}/outcomes` | 记录实际结果、证据与归因不确定性 | REQ-007 |
| `POST` | `/v1/feedback` | 提出纠正、异议或申诉 | REQ-007, REQ-011 |
| `GET` | `/v1/feedback/{id}` | 跟踪纠错与申诉处理 | REQ-007, REQ-011 |
| `POST` | `/v1/experience-versions` | 从真实结果提炼有条件的候选经验 | REQ-008 |
| `GET` | `/v1/experience-versions/{id}` | 读取当前可见的经验版本 | REQ-008 |
| `POST` | `/v1/skill-versions` | 创建受工具权限约束的Skill候选 | REQ-009 |
| `GET` | `/v1/skill-versions/{id}` | 读取Skill版本 | REQ-009 |
| `POST` | `/v1/evaluation-runs` | 比较候选与基线，保留退化和未知 | REQ-010 |
| `GET` | `/v1/evaluation-runs/{id}` | 读取验证证据与结论 | REQ-010 |
| `POST` | `/v1/releases` | 校验证据与发布权后发布限定范围的经验或Skill | REQ-008, REQ-009, REQ-010 |
| `GET` | `/v1/releases/{id}` | 读取发布版本与作用范围 | REQ-009 |
| `POST` | `/v1/releases/{id}/withdrawals` | 停止新调用并处理等待中的旧版本任务 | REQ-009 |
| `GET` | `/v1/integrations` | 读取可见连接器状态与读写能力 | REQ-012 |
| `POST` | `/v1/integrations/{id}/syncs` | 模拟同步或执行已授权读取 | REQ-012 |
| `GET` | `/v1/jobs/{id}` | 读取持久后台作业状态 | REQ-006 |
| `GET` | `/v1/work-items/{id}/workspace` | 重新进入事项并读取有权查看的关联记录 | REQ-001, REQ-002, REQ-013 |
| `POST` | `/v1/work-items/{id}/participants` | 由有权者增加事项访问成员，不自动产生支持承诺 | REQ-001, REQ-014 |
| `POST` | `/v1/work-items/{id}/participants/{principal_id}/revocations` | 撤回事项成员访问并传播派生权限 | REQ-001, REQ-014 |
| `POST` | `/v1/work-items/{id}/ownership-transfers` | 提出负责人交接，原负责人继续负责直至有效接受 | REQ-001, REQ-004 |
| `GET` | `/v1/ownership-transfers/{id}` | 读取负责人交接请求 | REQ-001 |
| `POST` | `/v1/ownership-transfers/{id}/responses` | 由接收人或有效委托人明确承接交接 | REQ-001, REQ-004 |
| `GET` | `/v1/sources/{source_id}/versions/{version_id}` | 按当前权限读取来源历史内容与观察时间 | REQ-002 |
| `GET` | `/v1/corrections/{id}` | 读取纠错内容、处理理由与影响 | REQ-007, REQ-011 |
| `POST` | `/v1/corrections/{id}/resolutions` | 由来源责任人处理纠错并记录实际生效范围 | REQ-007, REQ-011 |
| `GET` | `/v1/capability-offers/{id}` | 读取当前可见的能力与共享约定 | REQ-003, REQ-011 |
| `PATCH` | `/v1/capability-offers/{id}` | 修订能力描述、证据和共享范围，保留历史 | REQ-003, REQ-011 |
| `POST` | `/v1/capability-offers/{id}/withdrawals` | 撤下后续能力发现与新请求，已有承诺另行处理 | REQ-003, REQ-011 |
| `GET` | `/v1/decisions/{id}` | 回读决定、依据、未知与风险 | REQ-001, REQ-005 |
| `GET` | `/v1/outcomes/{id}` | 回读实际结果、证据与归因边界 | REQ-007 |
| `POST` | `/v1/outcomes/{id}/verifications` | 由获准核实者验证、争议或保留未知 | REQ-007 |
| `POST` | `/v1/outcomes/{id}/revisions` | 更正结果并保留原记录及修订关系 | REQ-007 |
| `POST` | `/v1/feedback/{id}/resolutions` | 由受理者回复纠错、异议和申诉并关联处理证据 | REQ-007, REQ-011 |
| `POST` | `/v1/experience-versions/{id}/revisions` | 建立同主题的新内容版本并保留前版 | REQ-008 |
| `POST` | `/v1/experience-versions/{id}/confirmations` | 记录贡献者或维护人对内容与用途的确认 | REQ-008, REQ-011 |
| `POST` | `/v1/skill-versions/{id}/revisions` | 建立同Skill的新内容版本 | REQ-009 |
| `POST` | `/v1/skill-versions/{id}/confirmations` | 记录技能内容与用途确认，不自动授予执行权 | REQ-009, REQ-011 |
| `POST` | `/v1/usage-restrictions` | 按现有权利限制用途或提出需受理的变更请求 | REQ-011 |
| `GET` | `/v1/usage-restrictions/{id}` | 跟踪用途限制实际是否生效 | REQ-011 |
| `POST` | `/v1/usage-restrictions/{id}/resolutions` | 由有权责任人处理用途变更请求 | REQ-011 |
| `GET` | `/v1/resource-leads/{id}` | 读取允许发现的资源线索当前版本 | REQ-003 |
| `POST` | `/v1/resource-leads/{id}/confirmations` | 由有权维护人核实当前情境和可提供的帮助 | REQ-003 |
| `GET` | `/v1/source-access-revocations/{id}` | 读取撤权生效与后台清理的当前状态 | REQ-002, REQ-011, REQ-014 |
| `GET` | `/v1/inbox` | 读取本人或有效委托范围内的待处理支持、交接和审阅 | REQ-001, REQ-004, REQ-011, REQ-014 |
| `GET` | `/v1/support-responses/{id}` | 回读具体回应、接受条件和回应主体 | REQ-004 |
| `GET` | `/v1/support-fulfilments/{id}` | 回读实际帮助、证据和关联结果 | REQ-004, REQ-007 |
| `GET` | `/v1/support-supplements/{id}` | 回读补充资料与期限修订 | REQ-004 |
| `POST` | `/v1/support-requests/{id}/supplements` | 在待受理或补资料状态提交补充，保留原请求 | REQ-004 |
| `GET` | `/v1/action-attempts/{id}` | 读取实际执行尝试与回执关联 | REQ-006 |
| `GET` | `/v1/action-receipts/{id}` | 按当前权限回读真实或模拟回执证据 | REQ-006, REQ-007 |
| `POST` | `/v1/evaluation-runs/{id}/reviews` | 由独立审阅者针对准确报告版本确认或提出争议 | REQ-010 |
| `GET` | `/v1/evaluation-reviews/{id}` | 读取独立审阅依据与报告绑定 | REQ-010 |
| `GET` | `/v1/confirmations/{id}` | 读取内容及用途确认，不扩大执行权 | REQ-008, REQ-009, REQ-011 |
| `GET` | `/v1/source-versions/{id}/attachment` | 经当前权限检查代理读取来源附件 | REQ-002 |
| `GET` | `/v1/auth/login` | 开始OIDC登录 | REQ-014 |
| `GET` | `/v1/auth/callback` | 完成OIDC回调并建立会话 | REQ-014 |

## 4. 重要业务语义

### 持续工作空间与交接

`getWorkspace` 返回目标、当前未知及当前有权访问的记录引用。相关来源、决定、行动、结果、支持和Skill都有独立回读入口，不依赖浏览器旧聊天或内存。进入事项与切换参与者后，仍须逐个检查引用权限。

本人收件箱`getInbox`按当前主体及有效委托返回待处理支持、交接、纠错、用途请求和评测审阅的最小上下文及对象引用。收件人可读取为处理该请求已获准分享的内容，不自动成为整事项参与者；更深来源仍分别核权。送达只产生收件记录，不代表接受或批准。拒绝、过期、已处理和委托变更均更新收件状态。

增加参与者改变访问范围，不自动形成资源承诺。负责人交接先创建请求，原负责人继续存在；接收人或有效委托人明确接受后，在事务中重新检查成员资格、原负责人和事项版本，再完成交接。并发交接或期间已变更的事项返回冲突，不能由“通知已发出”推断接管。

Run持久保存原发起者、有效执行主体、委托引用、成员资格epoch、政策版本、预算/消耗/未知及步骤边界。后台服务按这些记录和当前资格恢复，不能继承新负责人的权限或使用worker账号的广泛权限；交接需要明确建立新run或重新授权。退出浏览器不会使任务记录消失，会员资格/委托撤销仍在每步生效。

每事项首版一个活动run；运行中目标变化、来源变化、预算或委托撤销会触发重判。Run完成、Action成功、Support履行和WorkItem成果分别核实。`completed`转换需要相应结果证据和结果确认政策；取消或保留未知不能被改写为成功。

### 贡献、纠错与来源

能力可读取、修订、变更共享范围及撤下；只允许相应贡献者或明确授权维护人操作。撤下停止新发现/新请求，已有承诺需要记录替代、交接或重新协商，不假装已消失。

来源按版本阅读。纠错先记录内容、证据与理由，再由事实责任人处理。本地来源接受纠错生成新版本并标记派生依赖；外部权威系统的记录不得被平台“接受纠错”直接覆盖，可以形成注解或待权威回写的请求，实际回写必须经过动作授权与回执。`Correction.effect`和`resulting_source_version_id`明确生效范围。

支持请求回读期限、背景、资源线索、接受条件及回应/补充/履行记录引用；这些引用分别通过getSupportResponse/getSupportSupplement/getSupportFulfilment读取原内容、主体、时间和证据。needs_info状态可由申请人提交补充，再进入待受理；已经接受的条件变更不能被补充命令静默替换，须重新协商。Action返回attempt_ids与receipt_id，可分别读取尝试与回执，按当前权限查证实际副作用。Feedback回读原诉求与证据；UsageRestriction分别返回申请范围/用途、申请理由、处理理由及实际生效范围；这些内容均按当前权限返回。

来源撤权先同步阻断访问，202返回撤权记录与job_id；getSourceRevocation和getJob可在刷新或清理失败后继续跟踪。

成员可跟踪Feedback、Correction和UsageRestriction的处理。用途限制可能依既有权利立即生效，也可能先进入请求；响应必须明确是 `applied` 还是 `requested`，以及当前实际范围。政策未确认时不虚构贡献者或管理员拥有无限处分权。

结果提交初始为reported；有权核实者可以验证、争议或保留未知。修订建立新记录、引用前一结果，保留原始经历；`verified`也不等于因果完全确定或经营收益全部归功于Agent。

### 授权审阅与外部执行

授权者通过GET Action阅读目标、参数、来源版本和服务端摘要，通过GET Decision阅读取舍，通过GET Authorization阅读被授权人、条件和预算。没有完整必要信息的授权者应请求相应核实或改由有权者处理，不能依赖脱敏后缺失的关键条件猜测批准。

模拟动作必须在记录和UI显著标明；模拟授权不能用于真实连接器。执行前再次验证身份、委托、期限、动作版本、摘要、预算、来源及工具专用约束。API字段允许创建建议，不表示公司已确认相应组织政策。

`reconcileAction`只记录获准的核实，不允许任意调用者声明外部成功。确认成功/失败须有证据，找不到可靠结果可提交unresolved并维持未知。新的失败记录不能掩盖可能已生效的旧尝试。

### 版本、确认与发布

ExperienceVersion和SkillVersion是有前版关联的内容版本；新修订保留原内容，并原子校验所属主题的当前修订关系。陈旧父版、重复续版或已撤回内容需要明确冲突处理；新候选不自动替换正在使用的已发布版本。

贡献者/维护人的确认记录用途与异议，不自动授予生产执行权。发布需要适用的确认、可核查评测、发布权限和范围。评测回读包含基线、suite/数据版本、模型/harness/工具/政策版本、受控报告引用、指标、人工与模型成本、限制和独立审阅记录。报告由获准的评测执行器记录，带report_version与服务端摘要；独立审阅者经reviewEvaluation提交确认、争议或需补充，后端验证其权限与独立性，绑定准确报告版本。重读可沿review_record_ids取得原审阅。报告改变后旧审阅保留但不能批准新版本，须重新审阅。报告证据不足或无权读取必要依据时，发布审阅不得仅凭一句improved通过。评测不充分或结论不明确时不认定能力已经改善。具体发布政策见POL-007。

撤回使新检索与新调用停止使用该发布，并找出等待/运行中的依赖；已经发生的外部动作不能因版本撤回而被删除。进行中的任务在下一检查点重判，必要时暂停或恢复已验证版本。

## 5. 错误和界面恢复

错误使用 `application/problem+json`：`type/title/status/code/detail/request_id/retryable`，可附恢复建议。恢复建议不能包含调用者无权知道的来源或人员信息。

| 状态 | 前端行为 |
|---|---|
| 401 | 保留未发送草稿，重新登录后重读事项，不能自动重放旧授权动作。 |
| 403/404 | 说明不可访问或缺少必要授权；不显示隐藏资源细节。 |
| 409 | 展示具体可见的状态、政策、预算或幂等冲突；按原因请求支持、核实或调整，不无限重试。 |
| 412/428 | 重读ETag与当前状态，允许成员比较后重新提交。 |
| 422 | 显示字段或工具专用约束错误；保留草稿。 |
| 429/503 | 仅对安全读取/明确可重试命令有限退避；未知外部动作先查回执。 |

接口schema验证只能证明结构有效；不会自动证明当前用户有权批准、联系人关系可靠、结果真实或Skill有效。运行与产品验证见[VERIFICATION.md](VERIFICATION.md)。
