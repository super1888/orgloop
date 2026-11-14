# 数据模型与知识生命周期

状态：逻辑/物理设计建议，2026-11-14。字段、约束与 SQL 片段用于约束后续实现，尚未形成或执行数据库迁移；不得将本页标为数据库测试通过。

关联：[需求](REQUIREMENTS.md)、[架构](ARCHITECTURE.md)、[API](API.md)、[运行机制](RUNTIME.md)、[决策](DECISIONS.md)、[验证](VERIFICATION.md)。

## 1. 数据原则

数据库保存组织在具体情境中的认识、承诺与行动。它不要求每条说法立即成为真/假，也不把一个人的整体价值压成一个分数。

1. 来源、陈述、推断、决定、行动和结果分别记录；引用一份资料不能证明其内容已经证实。
2. 人物身份、过去岗位、当前岗位、历史接触、当前可提供支持分别可修订。
3. 原系统负责约定范围内的权威记录；来源冲突保留差异，不让 Agent 自动覆盖。
4. 所有组织业务数据带 `organization_id`；跨对象引用使用同组织复合键，不能只靠前端过滤。
5. 聚合使用正整数 `version`。可公开的事实时间与内部同步时间分开，业务发生时间不由同步时间替代。
6. 来源和经验的适用范围、访问范围、有效时间和维护人是数据的一部分。

## 2. 身份、来源与资源

UUID 为资源标识。下表中除全局 `principal` 外，业务实体均有 `organization_id`、`id`、创建时间及必要的版本；API 是否暴露字段由 [API](API.md) 决定。交互命令的 `organization_id` 和实际操作者由后端会话推导，不接受写请求自行指定；后台运行使用创建时登记的执行上下文，并按当前政策复核，不能依赖浏览器会话持续存在。

| 实体 | 核心字段 | 键与约束 |
| --- | --- | --- |
| `organization` | `id`, `name`, `policy_version` | 组织是隔离边界；名称不作为安全标识 |
| `principal` / `membership` | `principal_id`, `kind`, `organization_id`, `status`, `epoch`, `identity_provider_ref` | 账号与人物资料分开；成员唯一键 `(organization_id, principal_id)`，资格/角色等授权相关变化递增membership epoch |
| `entity` | `id`, `entity_type`, `display_name`, `identity_state` | 客户、项目、场地、资产、人员等；实体合并保留依据与可逆映射 |
| `external_ref` | `entity_id`, `connector_id`, `source_object_type`, `source_id`, `source_revision` | 同来源对象唯一；姓名或语义相似不足以自动合并身份 |
| `source_record` | `connector_id`, `source_id`, `latest_version_id`, `access_epoch`, `sync_state` | 保存当前来源及权限入口；删除/撤权不等于静默消失 |
| `source_version` | `source_record_id`, `source_revision`, `recorded_at`, `observed_at`, `synced_at`, `content_hash`, `content_ref`, `access_policy_ref` | 来源快照不可原位改写；权限按当前有效政策复查 |
| `claim` | `subject_entity_id`, `predicate`, `object_value/entity_id`, `kind`, `verification_state`, `valid_from/to`, `confirmed_by`, `supersedes_id` | `kind` 区分观察、来源方陈述、推断、假设；不确定值可保留 |
| `claim_evidence` | `claim_id`, `source_version_id`, `locator`, `relation` | 证据可支持或反驳陈述；定位到来源具体部分 |
| `capability_offer` | `owner_principal_id/entity_id`, `task_description`, `conditions`, `limits`, `evidence_refs`, `maintenance_owner`, `discovery_policy_ref` | 描述具体支持能力，不产生全员统一价值分 |
| `relationship_lead` | `from_entity_id`, `to_entity_id`, `contact_context`, `role_at_time`, `occurred_at`, `last_confirmed_at`, `claim_refs` | 历史接触不自动变成当前关系、意愿或授权 |
| `resource_offer` | `provider_principal_id`, `kind`, `support_description`, `conditions`, `availability_ref`, `request_policy_ref` | 可申请支持与已经承诺的支持分开；职位不自动形成授权 |

`claim.kind` 的推荐内部值为 `observation`、`source_statement`、`inference`、`hypothesis`；确认状态可为 `unverified`、`confirmed`、`disputed`、`superseded`、`withdrawn`。这些只表达认识状态，不是自动打分。来源明确的“曾在某岗位”仍不能直接推出“现在可批准采购”。

访问模式分别表达：允许发现线索、允许阅读原文、允许申请支持、允许执行动作。人物、联系线索和资源 offer 的可见范围必须由已确认政策决定；系统不能把存在于后台的所有人脉展示给所有成员。

## 3. 事项、承诺与执行

| 实体 | 核心字段 | 必要约束 |
| --- | --- | --- |
| `work_item` | `goal`, `created_by`, `owner_id`, `status`, `constraints`, `current_context_ref`, `version` | 目标与负责人持续存在；状态完成不自动证明业务成功 |
| `run` | `work_item_id`, `initiator_id`, `effective_principal_id`, `delegation_id`（可空）, `membership_epoch`, `policy_version`, `execution_scope_ref`, `context_valid_until`, `status`, `waiting_reason`, `model_version`, `harness_version`, `context_refs`, `budget_limit/consumed`, `step_limit/consumed` | 一次运行与长期事项分开；持久绑定发起者、有效执行主体和范围，不随负责人或worker变化继承新权限 |
| `support_request` | `work_item_id`, `requester_id`, `recipient_id`, `resource_offer_id`, `requested_support`, `due_at`, `status`, `response_ref`, `version` | 资源 owner 或已授权代理人回应；接受不等于实际履行 |
| `decision` | `work_item_id`, `question`, `options_ref`, `evidence_refs`, `assumptions`, `rationale_summary`, `decided_by`, `review_condition` | 模型建议与有权者决定分开；不保存完整模型内部推理 |
| `authorization` | `subject_principal_id`, `delegation_ref`, `action_id`, `proposal_version`, `payload_digest`, `action_scope`, `target_scope`, `budget`, `valid_until`, `status`, `policy_version` | 绑定不可变提案内容、主体、条件和期限；生命周期version变化不单独使内容绑定失效 |
| `action` | `work_item_id`, `run_id`, `proposal_version`, `payload_digest`, `authorization_id`, `idempotency_ref`, `status`, `version` | `version` 用于生命周期并发控制；`proposal_version` 用于授权内容绑定 |
| `action_proposal` | `action_id`, `proposal_version`, `tool_ref/version`, `target_ref`, `payload_ref`, `payload_digest`, `mode`, `critical_source_conditions` | 唯一键 `(organization_id, action_id, proposal_version)`；工具、目标、参数、模式和关键来源条件不可原位改写 |
| `action_attempt` | `action_id`, `attempt_number`, `lease_token`, `started_at`, `finished_at`, `remote_operation_id`, `receipt_ref`, `result_class` | 每次运输/调用尝试保留；超时不能擅自归类失败 |
| `outcome` | `work_item_id/action_id`, `observation`, `measured_at`, `measurements`, `evidence_refs`, `reported_by`, `review_state`, `unresolved` | 缺失测量不是零；业务归因不明确可保留争议 |
| `feedback` | `target_type/id/version`, `kind`, `content_ref`, `evidence_refs`, `submitted_by`, `resolution_ref` | 纠错、偏好和实际结果分开；反馈不立即覆盖事实 |

### 3.1 共用状态

| 对象 | 状态 |
| --- | --- |
| Work item | `open`, `active`, `waiting`, `blocked`, `completed`, `cancelled` |
| Run | `queued`, `running`, `waiting`, `blocked`, `completed`, `failed`, `cancelled` |
| Support request | `pending`, `accepted`, `needs_info`, `declined`, `withdrawn`, `expired`, `fulfilled` |
| Action | `proposed`, `awaiting_authorization`, `ready`, `executing`, `succeeded`, `failed`, `outcome_unknown`, `cancelled` |
| Experience / Skill version | `candidate`, `evaluating`, `released`, `superseded`, `withdrawn` |

`waiting_reason` 单列，不通过增加大量业务状态编码每种情境。资源请求的 `fulfilled` 需要关联履行记录；事项 `completed` 需要结果说明和适用确认，仍可记录业务没有达到预期或结论未决。

### 3.2 并发、幂等与事件

- 聚合 GET 返回 ETag，更新使用 `If-Match`；缺失返回 428，版本陈旧返回 412，不能静默覆盖。
- 新增及可能产生副作用的命令使用 `Idempotency-Key`，按组织、实际操作者和操作范围隔离。同键同规范化负载返回原结果；同键异负载返回 409。
- 幂等记录保留请求摘要、执行状态和结果引用，不保存无保护的密钥。重放结果前仍需检查当前身份和读取权限，撤权后不能靠重放取出旧内容。
- `work_item_event` 记录事项内单调递增游标、类型、时间和可见负载。前端按游标分页获取；事件与对象同样受权限约束。
- 领域状态、事件、job/outbox 必须在同一内部事务提交。对外调用在事务外执行，结果通过后续受并发控制的事务记录。

### 3.3 后台执行身份

run 的执行上下文与其计划内容一同持久化。`initiator_id` 记录谁发起，`effective_principal_id` 记录代表谁执行，`delegation_id` 引用适用委托（本人执行时可空）；`membership_epoch` 保存该有效主体的membership epoch，连同 `policy_version` 与范围引用识别权限或政策变化，预算和步骤上限持续对账。

worker 的服务账号只负责领取和处理任务，不把自身数据库或连接器能力当作 run 的业务权限。读取资料、发送支持请求、调用模型/工具及恢复前，以已登记执行主体和用途复核当前成员资格、委托、撤权、政策与资源范围。有效权限不得超过登记范围与当前权限的交集；发现 epoch/政策变化时触发复核或暂停，不能自动填入更高权限继续。

浏览器会话过期或发起者离线，不提供额外授权，也不应靠复用旧Cookie执行。允许离线推进的期限和范围以已登记上下文及已确认政策为准。成员资格撤回、委托失效或用途不再有效时，旧run停止受影响的后续读取和写入。

负责人交接只改变事项责任，不修改旧run的 `effective_principal_id` 或使其继承新负责人的权限。需要新身份或扩大范围时，记录明确的重新授权或建立新run，并处理旧run及在途动作；不静默重绑历史身份。来源同步等服务任务也须有单独登记的服务执行上下文，不能借此任意读入所有组织资料。

### 3.4 提案内容版本与生命周期版本

授权绑定 `(action_id, proposal_version, payload_digest)`，并继续检查主体、期限、预算和当前来源条件。`ActionBinding.proposal_version` 与 Action 返回的 `proposal_version` 一致；不能使用生命周期 `version` 代替该绑定。

例如，提案版本1、摘要D被授权后，action从ready进入executing或outcome_unknown，生命周期version随状态变化递增，内容仍是提案1/D。只要当前授权和其他条件仍有效，合法状态变更不会单独使内容授权失效；ETag仍用于阻止并发覆盖。

更改工具、目标、参数、模拟/真实模式或关键来源条件，必须建立新不可变提案版本或新action，重新授权并使用相应幂等语义。不能为恢复执行而忽略版本检查，也不能在原动作仍执行中或结果未知时改写其已发送内容及回执标识。

对于 `outcome_unknown`，先核实既有动作。原写授权过期时，只读回执查询可依据核实者独立、现行且范围适当的读权限进行，并记录实际核实主体；这不恢复旧run权限、不续期写授权，也不允许重试、撤销或补偿等写动作。重试写入需要重新有效的授权。

## 4. 经验、Skill 与评测

| 实体 | 核心字段 | 意义 |
| --- | --- | --- |
| `experience` | `id`, `owner_id`, `contributors`, `current_version_id` | 持续维护的经验主题 |
| `experience_version` | `experience_id`, `version_number`, `state`, `case_refs`, `context`, `method`, `conditions`, `counterexamples`, `limitations`, `visibility_policy_ref` | 一份有条件的认识；候选状态不代表已证实通用 |
| `skill` / `skill_version` | `kind`, `input/output_contract`, `guidance_ref`, `allowed_tool_refs`, `conditions`, `evaluation_refs`, `state`, `maintenance_owner` | 首版为指导或受控工具组合；不能自行获得任意代码执行权 |
| `evaluation_run` | `candidate_ref`, `baseline_ref`, `dataset_version`, `model/harness/tool_versions`, `results_ref`, `costs`, `reviewer`, `limitations` | 保留未见案例、回归、失败和代价；仅模型互评不足以证明效果 |
| `artifact_dependency` | `dependent_type/id/version`, `source_type/id/version`, `use_kind`, `access_epoch` | 定位事实更正、来源撤权和经验退化影响的派生内容 |

发布版本不可原位覆盖。修改方法、条件、可见范围或工具集合时产生新版本，旧版本可 supersede 或 withdraw。发布授权和组织政策修改权分别管理；发布 Skill 不得附带扩大公司预算、数据权限或人员评价规则。

后续权重训练是独立项目，需另有用途、数据范围、保留与评测决策。首版不把模型权重作为经常变化的人员关系、权限、库存或合同事实的权威存储。

## 5. SQL 约束示意

以下是待迁移验证的说明性片段，省略关联表、完整策略、索引及时间戳；不是可直接部署的完整 DDL。

```sql
CREATE TABLE work_item (
    organization_id uuid NOT NULL,
    id uuid NOT NULL,
    created_by uuid NOT NULL,
    owner_id uuid NOT NULL,
    goal text NOT NULL,
    status text NOT NULL CHECK (status IN
      ('open','active','waiting','blocked','completed','cancelled')),
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (organization_id, id),
    FOREIGN KEY (organization_id, owner_id)
      REFERENCES membership (organization_id, principal_id),
    FOREIGN KEY (organization_id, created_by)
      REFERENCES membership (organization_id, principal_id)
);

CREATE TABLE support_request (
    organization_id uuid NOT NULL,
    id uuid NOT NULL,
    work_item_id uuid NOT NULL,
    recipient_id uuid NOT NULL,
    requested_support text NOT NULL,
    status text NOT NULL CHECK (status IN
      ('pending','accepted','needs_info','declined',
       'withdrawn','expired','fulfilled')),
    version bigint NOT NULL DEFAULT 1 CHECK (version > 0),
    PRIMARY KEY (organization_id, id),
    FOREIGN KEY (organization_id, work_item_id)
      REFERENCES work_item (organization_id, id),
    FOREIGN KEY (organization_id, recipient_id)
      REFERENCES membership (organization_id, principal_id)
);
```

事务内的条件更新使用 `(organization_id, id, version)`，受影响行数为零时返回版本冲突，不继续追加成功事件。实际迁移还需验证成员离职后的历史引用保留方式、删除策略、状态转换规则与事件顺序。

RLS 示意：

```sql
ALTER TABLE work_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE work_item FORCE ROW LEVEL SECURITY;
CREATE POLICY organization_boundary ON work_item
  USING (organization_id =
    NULLIF(current_setting('app.organization_id', true), '')::uuid)
  WITH CHECK (organization_id =
    NULLIF(current_setting('app.organization_id', true), '')::uuid);
```

该策略仅示意组织隔离。执行角色必须非超级用户、非 `BYPASSRLS`，迁移角色和应用角色分离；组织上下文来自后端已认证会话或经当前政策复核的持久执行上下文，事务内设置，不能由请求负载或队列消息任意指定。对象级、字段级、原文/线索/申请/执行权限仍由后端政策服务控制。池化连接、worker、索引和备份恢复均需独立验证。

## 6. 索引与存储建议

- 事项列表：组织、负责人、状态、更新时间；事件：组织、事项、游标唯一。
- 来源关联：组织、连接器、来源对象类型、来源 ID 唯一；来源版本及内容 hash 辅助去重但不能合并权限。
- 请求：组织、接收人、状态、到期时间；行动：组织、事项、状态、外部操作标识。
- 任务领取：可执行时间、状态、优先次序、租约；租约 token 防止旧 worker 覆盖新记录，但不能阻止无幂等外部副作用。
- 搜索：授权范围、实体、时间和版本过滤后检索全文/向量候选，并在返回内容前复查。向量相似度只用于相关性，不作为真假或人的能力等级。
- 附件：数据库保存受控引用、hash、类型、大小和来源版本。对象存储 key 不承担授权，不能直接公开桶或长期裸 URL。

## 7. 更正、撤权与保留

1. 来源更新生成新版本，当前陈述可 supersede；历史案例继续保留“当时依据”，不把新事实伪装成当时已知。
2. 撤权或删除事件先更新当前访问入口与 `access_epoch`，立即阻止新读取、分享和执行使用。
3. 根据依赖图标记受影响的 chunk、embedding、摘要、经验和 Skill，执行重建、降级或撤回。索引延迟不能绕开访问入口。
4. 合法扩展派生内容的共享范围，需要授权人员确认用途及去敏版本；自动摘要或去姓名本身不能扩大权限。
5. 已批准经验的事实被反驳时保留原版本和纠正记录，停止其无条件复用；审计可保留必要元数据，原文保留期限与删除要求由公司政策决定。
6. 已经发送给外部模型或其他合法接收方的信息不能靠本库撤销实现“从未发生”。相关用途、出口和保留政策必须在接入前决定。

## 8. 合成经验样例

以下为合成示例，不对应任何真实公司、客户或人员。

某数据中心扩容事项中，项目系统记载施工结束，合同要求资产清单和端口映射报告，尚未检索到对应报告。Agent 提出“材料缺口可能阻碍验收”的假设，负责人核实后，Agent 汇集资产和现场资料，工程师检查，授权人员提交。客户确认材料满足要求；正式验收仍等待独立记录。

可复用经验是“对照合同、资产与现场证据检查交付材料缺口”，其条件和不同客户的差异需要保留。不得从材料齐全推出现场质量合格，也不得把一次材料补齐当成项目验收或收益已兑现。

## 9. 数据验证入口

REQ-001/REQ-004/REQ-006 需要并发、事务、幂等、重启恢复和回执未知的真实数据库测试；REQ-002/REQ-007/REQ-011/REQ-014 需要来源冲突、身份误合并、跨组织、撤权和成员纠错测试；REQ-008/REQ-009/REQ-010 需要经验发布与失效传播测试。

当前只定义上述行为，迁移、RLS 和运行效果均未执行验证。详细执行状态见 [验证文档](VERIFICATION.md)。
