# Data Dictionary Maker-Checker 数据流说明

## 1. 目的

本文档用于说明 maker-checker 数据模型中各张表的职责，以及新增、修改、删除在 submit、approve、reject 各阶段的数据库操作方式。

本文档面向：

- 后端开发
- 前端开发
- BA
- reviewer

## 2. 各张表的职责

### 2.1 当前正式表

#### `table_entity`

- 存储当前已经正式发布的 dataset 记录。
- 这是最终对外提供给用户查询和展示的 dataset 当前态。
- 只有审批通过后的数据才应该写入这张表。

关键治理字段：

- `version_seq`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

#### `attribute_entity`

- 存储当前已经正式发布的 attribute 记录。
- 这是最终对外提供给用户查询和展示的 attribute 当前态。
- 只有审批通过后的数据才应该写入这张表。

关键治理字段：

- `version_seq`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

### 2.2 审批请求头表

#### `approval_request`

- 表示一次 maker 的 submit 行为。
- 一次点击 `Submit` 应生成一个 `request_id`。
- 一个 request 可以包含一个或多个 dataset / attribute 变更。
- dashboard 的 tab 应主要基于这张表按 request 维度查询。

关键字段：

- `request_id`
- `source_type`
- `domain_id`
- `tenant_unique_id`
- `submitted_by`
- `submitted_at`
- `maker_comment`
- `request_status`
- `reviewed_by`
- `reviewed_at`
- `checker_comment`
- `total_items`
- `approved_items`
- `rejected_items`

### 2.3 待审批表

#### `table_entity_pending`

- 存储待审批的 dataset 变更。
- 每一行表示某个 request 下的一条 dataset 级别待审批明细。
- 用于 dashboard 中的 request detail 展示。

#### `attribute_entity_pending`

- 存储待审批的 attribute 变更。
- 每一行表示某个 request 下的一条 attribute 级别待审批明细。
- 用于 dashboard 中的 request detail 展示。

pending 两张表共享的重要字段：

- `request_id`
- `target_*_id`
- `dictionary_action`
- `approval_status`
- `current_version_seq`
- `target_version_seq`
- `requester_id`
- `requester_ts`
- `approver_id`
- `approver_ts`
- `maker_comment`
- `checker_comment`
- `current_snapshot`
- `validation_errors`

### 2.4 历史表

#### `table_entity_history`

- 存储 dataset 的历史版本。
- 当 update 或 delete 被审批通过并关闭旧版本时，旧版本写入这里。

#### `attribute_entity_history`

- 存储 attribute 的历史版本。
- 当 update 或 delete 被审批通过并关闭旧版本时，旧版本写入这里。

### 2.5 权限映射表

#### `tenant_role_mapping`

- 存储 tenant 级别的 requester / approver / viewer AD group 映射。
- 用于做角色判断。
- 不存 request，也不存 pending 数据。

## 3. 总体生命周期规则

核心规则是：

1. Maker 提交变更。
2. 数据先写入 `approval_request` 和 pending 表。
3. Submit 时不修改 current 正式表。
4. 由 checker 的 approve 或 reject 决定是否发布。

也就是说：

- `approval_request` 和 pending 表表示流程中的数据
- current 表表示已发布数据
- history 表表示已关闭的旧版本

## 4. 新增 Flow

场景：

- maker 新增一个 dataset
- maker 同时新增该 dataset 关联的 attributes

### 4.1 Maker submit

#### Step 1: 创建 request 头

向 `approval_request` 插入一条记录。

典型赋值：

- `request_id = 新 UUID`
- `source_type = 'UI'` 或 `'UPLOAD'`
- `domain_id = 目标 domain`
- `tenant_unique_id = 目标 tenant`
- `submitted_by = maker employee id`
- `submitted_at = now()`
- `maker_comment = submit comment`
- `request_status = 'PENDING'`
- `total_items = 1 + attribute 数量`

#### Step 2: 创建 dataset pending

向 `table_entity_pending` 插入一条记录。

典型赋值：

- `request_id = request 头的 id`
- `target_table_id = NULL` 或预生成 dataset id
- `dictionary_action = 'A'`
- `approval_status = 'P'`
- `current_version_seq = NULL`
- `target_version_seq = 1`
- `requester_id = maker`
- `requester_ts = now()`
- `current_snapshot = NULL`
- `table_metadata = 新增 dataset 的完整 payload`

#### Step 3: 创建 attribute pending

每个新 attribute 往 `attribute_entity_pending` 插一条记录。

典型赋值：

- `request_id = 同一个 request id`
- `target_attribute_id = NULL` 或预生成 attribute id
- `dictionary_action = 'A'`
- `approval_status = 'P'`
- `current_version_seq = NULL`
- `target_version_seq = 1`
- `requester_id = maker`
- `requester_ts = now()`
- `current_snapshot = NULL`
- `metadata = 新增 attribute 的完整 payload`

### 4.2 Pending Requests 展示

submit 后：

- request 会因为 `approval_request.request_status = 'PENDING'` 而出现在 pending 列表
- 明细来自 `table_entity_pending` 和 `attribute_entity_pending`

### 4.3 Checker approve

#### Step 1: 更新 request 头

更新 `approval_request`：

- `request_status = 'APPROVED'`
- `reviewed_by = checker`
- `reviewed_at = now()`
- `checker_comment = checker comment`
- `approved_items = total_items`
- `rejected_items = 0`

#### Step 2: 发布 dataset 到 current 表

向 `table_entity` 插入一条正式记录。

典型赋值：

- `id = target_table_id` 或新 id
- `version_seq = 1`
- `dictionary_action = 'A'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `requester_id = maker`
- `approver_id = checker`
- `requester_ts = submit time`
- `approver_ts = approve time`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`
- `table_metadata = 审批通过后的 pending payload`

#### Step 3: 发布 attributes 到 current 表

向 `attribute_entity` 插入正式记录。

典型赋值：

- `version_seq = 1`
- `dictionary_action = 'A'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`

#### Step 4: 更新 pending 行

更新对应 pending 行：

- `approval_status = 'A'`
- `approver_id = checker`
- `approver_ts = now()`
- `checker_comment = checker comment`

纯新增通常不需要写 history，因为没有旧版本需要关闭。

### 4.4 Checker reject

reject 不会发布到 current 表。

只更新：

- `approval_request.request_status = 'REJECTED'`
- request 的 review 字段
- pending 的 `approval_status = 'R'`
- pending 的 review 字段

current 表和 history 表都不变。

## 5. 修改 Flow

场景：

- maker 修改一个已有 dataset
- 或 maker 修改已有 attribute

### 5.1 Maker submit

#### Step 1: 创建 request 头

向 `approval_request` 插入一条记录。

#### Step 2: 创建 dataset update pending

向 `table_entity_pending` 插入一条记录。

典型赋值：

- `target_table_id = 已存在 dataset id`
- `dictionary_action = 'U'`
- `approval_status = 'P'`
- `current_version_seq = 当前版本号`
- `target_version_seq = 当前版本号 + 1`
- `current_snapshot = 当前已发布 dataset 快照`
- `table_metadata = 修改后的 dataset payload`

#### Step 3: 创建 attribute update pending

每个被修改的 attribute 往 `attribute_entity_pending` 插一条记录。

典型赋值：

- `target_attribute_id = 已存在 attribute id`
- `dictionary_action = 'U'`
- `approval_status = 'P'`
- `current_version_seq = 当前版本号`
- `target_version_seq = 当前版本号 + 1`
- `current_snapshot = 当前已发布 attribute 快照`
- `metadata = 修改后的 attribute payload`

这也是 dashboard 能做 old/new 对比的基础。

### 5.2 Checker approve

#### Step 1: 更新 request 头

将 `approval_request` 更新为 approved。

#### Step 2: 归档旧 dataset 版本

向 `table_entity_history` 插入一条记录。

典型赋值：

- `table_id = 当前 dataset id`
- `table_metadata = 旧 current payload`
- `version_seq = 旧版本号`
- `effective_from = 旧 current effective_from`
- `effective_to = approve time`
- `source_request_id = request_id`

#### Step 3: 更新 current dataset 行

更新 `table_entity`：

- `table_metadata = 新 approved payload`
- `version_seq = target_version_seq`
- `dictionary_action = 'U'`
- `approval_status = 'A'`
- `record_status = 'A'`
- `requester_id = maker`
- `approver_id = checker`
- `requester_ts = submit time`
- `approver_ts = approve time`
- `effective_from = approve time`
- `effective_to = NULL`
- `latest_request_id = request_id`

#### Step 4: 归档旧 attribute 并更新 current attribute

每个被修改的 attribute：

1. 将旧 current 行写入 `attribute_entity_history`
2. 将 `attribute_entity` current 行更新成审批通过的新版本

### 5.3 Checker reject

reject 只更新：

- `approval_request`
- pending 行

current 表和 history 表都不变。

## 6. 删除 Flow

场景：

- maker 删除一个 dataset

最新确认规则：

- dataset 删除审批通过后，该 dataset 下所有 attributes 都要软删除

### 6.1 Maker submit

#### Step 1: 创建 request 头

向 `approval_request` 插入一条记录。

#### Step 2: 创建 dataset delete pending

向 `table_entity_pending` 插入一条记录。

典型赋值：

- `target_table_id = 已存在 dataset id`
- `dictionary_action = 'D'`
- `approval_status = 'P'`
- `current_version_seq = 当前 dataset 版本号`
- `current_snapshot = 当前已发布 dataset 快照`
- `table_metadata = 当前 payload` 或带 delete 标记的 payload

#### Step 3: 不创建子 attribute delete pending

根据最新确认规则：

- dataset delete submit 时，不需要为关联的 attributes 额外生成删除 request
- submit 阶段只写 dataset 级别的 delete pending

原因是：

- 一个 dataset 可能关联大量 attributes
- 如果 submit 时为所有 child attributes 都生成 pending，会造成 request 明细过大
- 关联 attribute 的软删除改为在 approve 发布阶段统一处理

### 6.2 Checker approve

#### Step 1: 更新 request 头

将 `approval_request` 更新为 approved。

#### Step 2: 软删除 current dataset

更新 `table_entity`：

- `dictionary_action = 'D'`
- `record_status = 'D'`
- `approval_status = 'A'`
- `approver_id = checker`
- `approver_ts = approve time`
- `latest_request_id = request_id`

根据最终版本策略：

- 可以保留 current 行，只是标记为 disabled current state
- 也可以把旧版本归档后，把 delete 视为关闭版本

#### Step 3: 软删除所有关联 attributes

对于该 dataset 下所有 current attributes：

- 更新 `attribute_entity.record_status = 'D'`
- 更新 `attribute_entity.dictionary_action = 'D'`
- 更新 `attribute_entity.approval_status = 'A'`
- 更新 `attribute_entity.approver_id = checker`
- 更新 `attribute_entity.approver_ts = approve time`
- 更新 `attribute_entity.latest_request_id = request_id`

这一点必须由应用层 publish 逻辑显式完成。

它不会由 schema 自动保证。

#### Step 4: 按需要写 history

如果需要保留关闭前的旧版本，则写入 dataset 和 attribute history。

### 6.3 Checker reject

reject 只更新：

- `approval_request`
- pending 行

current 表和 history 表都不变。

## 7. Dashboard Tab 映射

dashboard 的 tab 列表应该主要基于 `approval_request`。

pending 表用于 request detail 展开，不建议直接作为 tab 主列表来源。

### 7.1 未登录用户

- 可以进入 dashboard
- `Pending Requests`：所有 `request_status = 'PENDING'` 的 request
- `My Requests`：不展示

### 7.2 已登录 maker

- `Pending Requests`：当前用户提交且 `request_status = 'PENDING'` 的 request
- `My Requests`：当前用户提交且 `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')` 的 request

### 7.3 已登录 checker

- `Pending Requests`：当前 checker 的 approver tenant scope 内、等待审批的 pending request
- `My Requests`：当前用户提交且 `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')` 的 request

### 7.4 同时是 maker 和 checker 的登录用户

- `Pending Requests`：以下两类并集
  - 当前用户自己提交且仍 pending 的 request
  - 当前用户审批范围内等待审批的 pending request
- `My Requests`：当前用户提交且 `request_status IN ('APPROVED', 'REJECTED', 'PARTIALLY_APPROVED')` 的 request

pending request 结果应按 `request_id` 去重。

## 8. 关键实现说明

### 8.1 request 级查询和 item 级查询的区别

`approval_request` 才是 dashboard tab 的正确主数据源。

pending 表是 item 级 detail，不应直接作为 tab 主列表来源。

### 8.2 删除联动是应用逻辑

“dataset 删除审批通过后，其子 attributes 全部软删除”这条规则，不会由外键或约束自动完成。

它必须在 approval publish transaction 中由服务层显式实现。

### 8.3 版本和 history 行为

- add：直接发布到 current，没有旧版本可归档
- update：旧 current 写入 history，新 approved 版本覆盖 current
- delete：current 被置为 disabled，child attributes 也同时被置为 disabled

## 9. 总结

这套模型应这样理解：

- `approval_request`：一次 submit 行为
- `table_entity_pending` / `attribute_entity_pending`：待审批明细
- `table_entity` / `attribute_entity`：当前正式数据
- `table_entity_history` / `attribute_entity_history`：历史归档版本
- `tenant_role_mapping`：tenant 级角色映射

整个生命周期是：

1. maker submit
2. 创建 request 头和 pending 行
3. checker review
4. approve 时发布到 current，并在需要时归档 history
5. reject 时只更新 request 和 pending 状态
