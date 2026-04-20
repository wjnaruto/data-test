# Data Dictionary Service Maker-Checker 数据模型设计

## 1. 目标

基于你当前 Data Dictionary Service 的现有数据模型：

- `domain_entity`
- `tenant_entity`
- `table_entity`（业务语义上对应本次需求中的 `dataset`）
- `attribute_entity`

定义一套可以支撑本次 Maker-Checker 需求开发的目标数据模型。

本设计目标是：

1. 尽量复用现有表结构和现有 `jsonb + generated columns` 模式
2. 尽量减少对现有读路径和现有搜索逻辑的破坏
3. 补齐审批暂存、版本、历史、审计、tenant 级权限映射能力
4. 支撑以下两类变更入口：
   - bulk upload
   - UI row-level add / edit / delete / submit

## 2. 现有数据模型解读

根据你提供的图片，当前模型大致如下：

### 2.1 `domain_entity`

- 保存 domain 级元数据
- 主要字段来源于 `metadata jsonb`
- 关键结构：
  - `id`
  - `name`
  - `fqnhash`
  - `metadata`
  - `updatedat`
  - `updatedby`
  - `createdat`
  - `metadata_text`

### 2.2 `tenant_entity`

- 保存 tenant 级元数据
- 通过 `domain_id` 关联 `domain_entity`
- 主要字段来源于 `metadata jsonb`
- 关键结构：
  - `id`
  - `name`
  - `metadata`
  - `domain_id`
  - `updatedat`
  - `updatedby`
  - `createdat`
  - `metadata_text`
  - `name_description`

### 2.3 `table_entity`

说明：

- 这张表虽然物理命名是 `table_entity`
- 但在本次需求语义里，应视为 `dataset`

现有特征：

- 保存 dataset 级元数据
- 通过 `domain_id`、`tenant_unique_id` 关联 domain / tenant
- 主业务 JSON 字段是 `table_metadata`
- 关键结构：
  - `id`
  - `table_name`
  - `tenant_name`
  - `table_metadata`
  - `updatedat`
  - `updatedby`
  - `deleted`
  - `createdat`
  - `attributes_metadata`
  - `domain_id`
  - `tenant_unique_id`
  - `table_metadata_text`
  - `name_description`

### 2.4 `attribute_entity`

- 保存 attribute 级元数据
- 通过 `table_id` 关联 `table_entity`
- 主业务 JSON 字段是 `metadata`
- 关键结构：
  - `id`
  - `field_name`
  - `table_name`
  - `tenant_name`
  - `metadata`
  - `updatedat`
  - `updatedby`
  - `deleted`
  - `createdat`
  - `domain_id`
  - `tenant_unique_id`
  - `tenant_id`
  - `table_id`
  - `metadata_text`
  - `name_description`
  - `table_description`

## 3. 现有模型与新需求之间的 Gap

当前模型可以很好支撑：

- 元数据存储
- 层级关系管理
- 搜索字段抽取
- dataset / attribute 展示

但无法直接支撑：

1. Maker-Checker 审批流
2. Pending staging 区
3. request 级批量提交流程
4. 审批 comments
5. 正式版本管理
6. 历史版本留存
7. 审计日志
8. tenant 级角色映射
9. 防重复提交与版本冲突控制

## 4. 设计结论

## 4.1 总体设计原则

建议采用“最小侵入改造”：

- 保留现有 `domain_entity / tenant_entity / table_entity / attribute_entity`
- 保留现有 `jsonb + generated columns` 设计
- 不建议在一期把现有模型整体重构成完全范式化设计
- 新增审批、历史、角色映射表来承接 Maker-Checker 能力
- 对当前 published 表，只增加必要的治理字段

## 4.2 一期建议作用范围

### 必做范围

- `table_entity`（dataset）
- `attribute_entity`

### 建议保持只读参考范围

- `domain_entity`
- `tenant_entity`

原因：

- 从需求原文和 UI 流程看，本次真正发生 add / edit / delete / upload / approve 的主要对象是 dataset 和 attribute
- `domain` 和 `tenant` 更像层级和归属维度，而不是一期自助治理的核心对象
- 如果后续需要对 `domain`、`tenant` 也做审批流，可以复用同一模式扩展

## 4.3 推荐目标模型

推荐引入以下数据层：

### A. 现有 published current tables

- `domain_entity`
- `tenant_entity`
- `table_entity`
- `attribute_entity`

### B. 新增审批头表

- `approval_request`

### C. 新增审批暂存表

- `table_entity_pending`
- `attribute_entity_pending`

### D. 新增历史版本表

- `table_entity_history`
- `attribute_entity_history`

### E. 新增权限映射表

- `tenant_role_mapping`

### F. 现有 published tables 补充治理字段

- 对 `table_entity`
- 对 `attribute_entity`

增加 maker-checker / version / effective window 相关字段

## 5. 为什么推荐“审批头表 + mirror pending/history 表”

相比“一个泛化 approval_item 表”，这里更推荐：

- 一个 `approval_request` 头表
- 两个 mirror pending 表
- 两个 mirror history 表

原因是：

1. 你当前核心业务表已经明确拆成 dataset 和 attribute 两类
2. 现有表大量依赖 `jsonb + generated stored columns`
3. 如果 pending/history 表镜像当前表结构，迁移和查询会简单很多
4. dashboard 查询可以通过 view 或 union 做统一聚合
5. 对开发团队来说更直观，也更利于后续排查数据问题

## 6. 目标数据模型定义

## 6.1 `domain_entity`

### 处理建议

- 一期不做结构性变更
- 保持 reference/master 数据角色
- 继续作为 `tenant_entity`、`table_entity` 的上游引用

### 是否增加 maker-checker 字段

- 一期不建议增加
- 如果后续 domain 也支持自助维护，再按 dataset 同样模式扩展

## 6.2 `tenant_entity`

### 处理建议

- 一期不建议直接增加审批和版本字段
- 继续作为 reference/master 数据角色
- tenant 的访问控制不要直接塞进 `tenant_entity.metadata`

### 原因

- AD group 映射是权限配置，不建议混进 tenant 业务 metadata
- 更适合通过独立表维护

## 6.3 `table_entity`（= dataset current published table）

### 处理建议

- 保持物理表名 `table_entity` 不变，避免大面积改代码和改外键
- 在业务文档和接口层，把它解释为 `dataset`
- 继续使用 `table_metadata jsonb` 作为业务元数据主体
- 新增显式治理字段，不建议把这些字段继续埋进 `table_metadata`

### 建议新增字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `requester_id` | `varchar(32)` | 否 | 最近一次获批变更的 Maker 员工号 |
| `approver_id` | `varchar(32)` | 否 | 最近一次批准该版本的 Checker 员工号 |
| `requester_ts` | `timestamptz` | 否 | Maker 提交该版本变更的时间 |
| `approver_ts` | `timestamptz` | 否 | Checker 批准该版本的时间 |
| `version_seq` | `integer` | 是 | 内部连续版本号，建议默认 `1` |
| `version_label` | `varchar(16)` 或 generated | 是 | 对外展示版本，例如 `1.0`、`2.0` |
| `dictionary_action` | `char(1)` | 是 | 最近一次获批动作，`A/U/D` |
| `approval_status` | `char(1)` | 是 | 当前 published 数据默认应为 `A` |
| `record_status` | `char(1)` | 是 | `A/D`，表示 active 或 disabled |
| `effective_from` | `timestamptz` | 是 | 当前版本开始生效时间 |
| `effective_to` | `timestamptz` | 否 | 当前版本结束生效时间，current 版本为空 |
| `latest_request_id` | `uuid` | 否 | 最近一次批准来源的 request |

### 兼容性建议

- 现有 `deleted bool` 字段不要移除
- 对于 delete / disable 场景：
  - 保持 `deleted = true`
  - 同时设置 `record_status = 'D'`

这样可以兼容旧逻辑和新逻辑

## 6.4 `attribute_entity`（current published table）

### 处理建议

- 和 `table_entity` 保持一致的治理模式
- 继续使用 `metadata jsonb` 作为业务元数据主体
- 增加显式治理字段

### 建议新增字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `requester_id` | `varchar(32)` | 否 | 最近一次获批变更的 Maker 员工号 |
| `approver_id` | `varchar(32)` | 否 | 最近一次批准该版本的 Checker 员工号 |
| `requester_ts` | `timestamptz` | 否 | Maker 提交该版本变更的时间 |
| `approver_ts` | `timestamptz` | 否 | Checker 批准该版本的时间 |
| `version_seq` | `integer` | 是 | 内部连续版本号 |
| `version_label` | `varchar(16)` 或 generated | 是 | 对外展示版本 |
| `dictionary_action` | `char(1)` | 是 | `A/U/D` |
| `approval_status` | `char(1)` | 是 | published 数据默认 `A` |
| `record_status` | `char(1)` | 是 | `A/D` |
| `effective_from` | `timestamptz` | 是 | 当前版本开始生效时间 |
| `effective_to` | `timestamptz` | 否 | 当前版本结束生效时间 |
| `latest_request_id` | `uuid` | 否 | 最近一次批准来源的 request |

### 兼容性建议

- 保持现有 `deleted bool`
- 与 `record_status` 双写，确保旧逻辑兼容

## 6.5 `approval_request`

### 用途

- 表示一次 Maker 提交
- 可用于 bulk upload，也可用于 UI submit
- 作为 request 级审批头

### 建议字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `request_id` | `uuid` | 是 | 主键 |
| `source_type` | `varchar(20)` | 是 | `UPLOAD` / `UI` |
| `domain_id` | `varchar(36)` | 是 | 对应 domain |
| `tenant_unique_id` | `varchar(36)` | 是 | 对应 tenant |
| `submitted_by` | `varchar(32)` | 是 | Maker 员工号 |
| `submitted_by_name` | `varchar(256)` | 否 | Maker 名称 |
| `submitted_at` | `timestamptz` | 是 | 提交时间 |
| `maker_comment` | `text` | 否 | Maker 总体备注 |
| `request_status` | `varchar(32)` | 是 | `PENDING / APPROVED / REJECTED / PARTIALLY_APPROVED` |
| `reviewed_by` | `varchar(32)` | 否 | Checker 员工号 |
| `reviewed_by_name` | `varchar(256)` | 否 | Checker 名称 |
| `reviewed_at` | `timestamptz` | 否 | 审批完成时间 |
| `checker_comment` | `text` | 否 | Checker 总体备注 |
| `source_file_name` | `varchar(512)` | 否 | bulk upload 文件名 |
| `source_file_hash` | `varchar(256)` | 否 | 文件 hash |
| `total_items` | `integer` | 是 | 提交记录数 |
| `approved_items` | `integer` | 是 | 已批准数 |
| `rejected_items` | `integer` | 是 | 已拒绝数 |
| `created_at` | `timestamptz` | 是 | 行创建时间 |
| `updated_at` | `timestamptz` | 是 | 行更新时间 |

### 索引建议

- `(tenant_unique_id, request_status, submitted_at desc)`
- `(submitted_by, submitted_at desc)`
- `(source_file_hash)`

## 6.6 `table_entity_pending`

### 用途

- 保存 dataset 的待审批版本
- 每一条记录对应一次 request 下的一条 dataset 变更

### 设计原则

- 尽量镜像 `table_entity`
- 保持 `table_metadata` + generated columns 模式
- 额外增加审批和版本相关字段

### 建议关键字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `pending_id` | `uuid` | 是 | 主键 |
| `request_id` | `uuid` | 是 | 所属 request |
| `target_table_id` | `varchar(36)` | 否 | 对应当前 published 的 dataset id，新增场景可为空或预生成 |
| `table_metadata` | `jsonb` | 是 | 待审批业务元数据 |
| `table_name` | generated | 是 | 由 `table_metadata` 提取 |
| `tenant_name` | generated | 是 | 由 `table_metadata` 提取 |
| `domain_id` | generated or column | 是 | domain |
| `tenant_unique_id` | generated or column | 是 | tenant |
| `dictionary_action` | `char(1)` | 是 | `A/U/D` |
| `approval_status` | `char(1)` | 是 | 默认 `P` |
| `current_version_seq` | `integer` | 否 | 当前 published 版本 |
| `target_version_seq` | `integer` | 否 | 如果获批后将成为的版本号 |
| `requester_id` | `varchar(32)` | 是 | Maker |
| `requester_ts` | `timestamptz` | 是 | Maker 提交时间 |
| `approver_id` | `varchar(32)` | 否 | Checker |
| `approver_ts` | `timestamptz` | 否 | Checker 审批时间 |
| `maker_comment` | `text` | 否 | Maker 备注 |
| `checker_comment` | `text` | 否 | Checker 备注 |
| `current_snapshot` | `jsonb` | 否 | 当前 published 版本快照 |
| `validation_errors` | `jsonb` | 否 | 行级校验错误 |
| `created_at` | `timestamptz` | 是 | 创建时间 |
| `updated_at` | `timestamptz` | 是 | 更新时间 |

### 约束建议

- `dictionary_action in ('A','U','D')`
- `approval_status in ('P','A','R')`
- 一个 `request_id + target_table_id + dictionary_action` 不应重复

## 6.7 `attribute_entity_pending`

### 用途

- 保存 attribute 的待审批版本
- 设计方式与 `table_entity_pending` 保持一致

### 建议关键字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `pending_id` | `uuid` | 是 | 主键 |
| `request_id` | `uuid` | 是 | 所属 request |
| `target_attribute_id` | `varchar(36)` | 否 | 对应当前 published 的 attribute id |
| `metadata` | `jsonb` | 是 | 待审批 attribute 业务元数据 |
| `field_name` | generated | 是 | 字段名 |
| `table_id` | generated or column | 是 | 所属 dataset |
| `table_name` | generated | 是 | 所属 dataset 名称 |
| `tenant_unique_id` | generated or column | 是 | tenant |
| `domain_id` | generated or column | 是 | domain |
| `dictionary_action` | `char(1)` | 是 | `A/U/D` |
| `approval_status` | `char(1)` | 是 | 默认 `P` |
| `current_version_seq` | `integer` | 否 | 当前 published 版本 |
| `target_version_seq` | `integer` | 否 | 获批后的目标版本 |
| `requester_id` | `varchar(32)` | 是 | Maker |
| `requester_ts` | `timestamptz` | 是 | Maker 时间 |
| `approver_id` | `varchar(32)` | 否 | Checker |
| `approver_ts` | `timestamptz` | 否 | Checker 时间 |
| `maker_comment` | `text` | 否 | Maker 备注 |
| `checker_comment` | `text` | 否 | Checker 备注 |
| `current_snapshot` | `jsonb` | 否 | 当前 published 快照 |
| `validation_errors` | `jsonb` | 否 | 校验错误 |
| `created_at` | `timestamptz` | 是 | 创建时间 |
| `updated_at` | `timestamptz` | 是 | 更新时间 |

## 6.8 `table_entity_history`

### 用途

- 保存 dataset 的历史关闭版本
- current published 表只保留当前版本
- history 表保留旧版本

### 为什么建议用 history 表而不是在主表中保留多版本

- 你当前主表主键和外键关系比较稳定
- `attribute_entity.table_id -> table_entity.id`
- 如果让 `table_entity` 同时存多版本，会牵扯现有外键和读取逻辑重构
- current table + history table 是对现有模型最稳妥的演进

### 建议关键字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `history_id` | `uuid` | 是 | 主键 |
| `table_id` | `varchar(36)` | 是 | 对应 current dataset id |
| `table_metadata` | `jsonb` | 是 | 该历史版本完整快照 |
| `version_seq` | `integer` | 是 | 历史版本号 |
| `version_label` | `varchar(16)` | 是 | 展示版本号 |
| `requester_id` | `varchar(32)` | 否 | 该版本 Maker |
| `approver_id` | `varchar(32)` | 否 | 该版本 Checker |
| `requester_ts` | `timestamptz` | 否 | 提交时间 |
| `approver_ts` | `timestamptz` | 否 | 批准时间 |
| `dictionary_action` | `char(1)` | 是 | 形成该版本的动作 |
| `approval_status` | `char(1)` | 是 | 通常为 `A` |
| `record_status` | `char(1)` | 是 | `A/D` |
| `effective_from` | `timestamptz` | 是 | 版本生效开始 |
| `effective_to` | `timestamptz` | 是 | 版本结束时间 |
| `source_request_id` | `uuid` | 否 | 来源 request |
| `archived_at` | `timestamptz` | 是 | 归档时间 |

### 唯一约束建议

- `unique(table_id, version_seq)`

## 6.9 `attribute_entity_history`

### 用途

- 保存 attribute 的历史关闭版本
- 结构与 `table_entity_history` 对齐

### 建议关键字段

- `history_id`
- `attribute_id`
- `metadata`
- `version_seq`
- `version_label`
- `requester_id`
- `approver_id`
- `requester_ts`
- `approver_ts`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `source_request_id`
- `archived_at`

### 唯一约束建议

- `unique(attribute_id, version_seq)`

## 6.10 `tenant_role_mapping`

### 用途

- 管理 tenant 级角色与 AD group 的映射
- 不建议把这部分塞进 `tenant_entity.metadata`

### 建议字段

| 字段名 | 类型 | 是否必填 | 用途 |
| --- | --- | --- | --- |
| `mapping_id` | `bigserial` 或 `uuid` | 是 | 主键 |
| `domain_id` | `varchar(36)` | 是 | domain |
| `tenant_unique_id` | `varchar(36)` | 是 | tenant |
| `role_type` | `varchar(20)` | 是 | `REQUESTER / APPROVER / VIEWER` |
| `ad_group_name` | `varchar(256)` | 是 | AD group 名 |
| `is_active` | `boolean` | 是 | 是否启用 |
| `created_at` | `timestamptz` | 是 | 创建时间 |
| `updated_at` | `timestamptz` | 是 | 更新时间 |

### 唯一约束建议

- `unique(tenant_unique_id, role_type)`

## 7. 核心关系定义

| From | To | 关系 | 说明 |
| --- | --- | --- | --- |
| `tenant_entity.domain_id` | `domain_entity.id` | N:1 | 现有关系保持不变 |
| `table_entity.domain_id` | `domain_entity.id` | N:1 | 现有关系保持不变 |
| `table_entity.tenant_unique_id` | `tenant_entity.id` | N:1 | 现有关系保持不变 |
| `attribute_entity.table_id` | `table_entity.id` | N:1 | 现有关系保持不变 |
| `approval_request.domain_id` | `domain_entity.id` | N:1 | request 所属 domain |
| `approval_request.tenant_unique_id` | `tenant_entity.id` | N:1 | request 所属 tenant |
| `table_entity_pending.request_id` | `approval_request.request_id` | N:1 | dataset pending 归属 request |
| `attribute_entity_pending.request_id` | `approval_request.request_id` | N:1 | attribute pending 归属 request |
| `table_entity_history.table_id` | `table_entity.id` | N:1 | dataset 历史版本归属 current dataset |
| `attribute_entity_history.attribute_id` | `attribute_entity.id` | N:1 | attribute 历史版本归属 current attribute |
| `tenant_role_mapping.tenant_unique_id` | `tenant_entity.id` | N:1 | tenant 角色映射 |

## 8. Add / Update / Delete 的落库规则

## 8.1 Add

### dataset add

1. Maker 提交后，在 `approval_request` 中生成一条 request。
2. 在 `table_entity_pending` 中生成待审批记录，`dictionary_action = 'A'`，`approval_status = 'P'`。
3. Checker approve 后：
   - 在 `table_entity` 插入新 current 记录
   - `version_seq = 1`
   - `version_label = '1.0'`
   - `effective_from = approver_ts`
   - `effective_to = null`

### attribute add

- 同样流程写入 `attribute_entity_pending`
- approve 后写入 `attribute_entity`

## 8.2 Update

### dataset update

1. Maker 提交后，在 `table_entity_pending` 保存 proposed version。
2. 同时记录当前 published 快照到 `current_snapshot`。
3. Checker approve 后：
   - 先把当前 `table_entity` 快照写入 `table_entity_history`
   - 历史记录的 `effective_to = 当前审批时间`
   - 更新 `table_entity` 当前行：
     - metadata 换成新版本
     - `version_seq = old + 1`
     - `version_label = n.0`
     - `effective_from = 当前审批时间`
     - `effective_to = null`

### attribute update

- 同理使用 `attribute_entity_history`

## 8.3 Delete

### dataset delete

1. Maker 提交 delete 请求，写入 `table_entity_pending`，`dictionary_action = 'D'`
2. Checker approve 后：
   - 建议先把原 current 快照写入 `table_entity_history`
   - 然后更新 `table_entity` 当前行：
     - `record_status = 'D'`
     - `deleted = true`
     - `dictionary_action = 'D'`
     - `effective_to = 当前审批时间`

### attribute delete

- 同理使用 `attribute_entity_history`

### 关于 delete 是否生成新版本

基于原始需求，建议一期默认：

- delete 不生成新的 `version_seq`
- 只关闭当前 current 记录并置为 disabled

如果业务后续要求“delete 也形成一个新的 disabled version”，再扩展

## 9. 关键约束与索引建议

## 9.1 Published current tables

### `table_entity`

- `check (dictionary_action in ('A','U','D'))`
- `check (approval_status in ('A','P','R'))`
- `check (record_status in ('A','D'))`
- `check (effective_to is null or effective_to >= effective_from)`

### `attribute_entity`

- 同上

## 9.2 Pending tables

### `table_entity_pending`

- 索引：
  - `(request_id)`
  - `(approval_status, requester_ts desc)`
  - `(tenant_unique_id, approval_status)`
  - `(target_table_id, approval_status)`

### `attribute_entity_pending`

- 索引：
  - `(request_id)`
  - `(table_id, approval_status)`
  - `(tenant_unique_id, approval_status)`

## 9.3 History tables

### `table_entity_history`

- `unique(table_id, version_seq)`
- 索引：
  - `(table_id, version_seq desc)`
  - `(tenant_unique_id, table_name)`

### `attribute_entity_history`

- `unique(attribute_id, version_seq)`
- 索引：
  - `(attribute_id, version_seq desc)`
  - `(table_id, field_name)`

## 10. 推荐实现方式

## 10.1 关于现有 `jsonb + generated columns` 模式

建议继续保留。

原因：

- 现有表就是围绕该模式建立的
- 搜索字段和展示字段都已经从 JSON 中抽取
- 一期不应该因为 maker-checker 需求就整体推翻现有模型

## 10.2 关于新治理字段

建议不要继续全部塞回原 JSON。

建议方式：

- 业务字段继续保存在原始 JSON 中
- maker-checker / version / effective window / request link 这些字段使用显式 relational columns

原因：

- 这些字段是系统控制字段，不是原始业务 metadata
- 需要做严格约束、索引和事务处理
- 用显式列更容易做审批、版本和历史管理

## 10.3 关于 dashboard 查询

建议增加一个 DB view 统一 pending 数据：

- `approval_dashboard_v`

它可以 `union all`：

- `table_entity_pending`
- `attribute_entity_pending`

输出统一字段：

- request_id
- entity_type
- entity_id
- entity_name
- tenant_unique_id
- domain_id
- dictionary_action
- approval_status
- requester_id
- requester_ts
- approver_id
- approver_ts

这样前端 dashboard 只需对接一个统一 query source。

## 11. 迁移建议

### 第一步

- 新增：
  - `approval_request`
  - `table_entity_pending`
  - `attribute_entity_pending`
  - `table_entity_history`
  - `attribute_entity_history`
  - `tenant_role_mapping`

### 第二步

- 为 `table_entity` 和 `attribute_entity` 增加治理字段

### 第三步

- 为现有 current 数据回填：
  - `version_seq = 1`
  - `version_label = '1.0'`
  - `approval_status = 'A'`
  - `record_status = case when deleted then 'D' else 'A' end`
  - `effective_from = 现有 createdat 或一次性初始化时间`

### 第四步

- 增加 dashboard view
- 增加历史查询接口和审批查询接口

## 12. 最终推荐结论

如果以“最符合你当前 service 的现状、同时又能支撑本次需求”为标准，我的推荐是：

1. 保留现有 `domain_entity / tenant_entity / table_entity / attribute_entity`
2. 把 `table_entity` 继续作为物理表名，但业务上等同于 `dataset`
3. 只对 `table_entity` 和 `attribute_entity` 加治理字段
4. 新增：
   - `approval_request`
   - `table_entity_pending`
   - `attribute_entity_pending`
   - `table_entity_history`
   - `attribute_entity_history`
   - `tenant_role_mapping`
5. current 表保留“当前版本”，history 表保留“旧版本”
6. pending 表保存待审批版本
7. delete 一期按“disable current record”实现，不默认生成新版本

这套设计是当前需求下最稳妥、最少破坏、最容易落地的一种方案。

## 13. 配套交付物

基于这份目标模型设计，当前已经补齐以下配套产物，便于数据库实现、开发排期和评审：

- PostgreSQL DDL 草案：
  - [data_dictionary_maker_checker_target_data_model_ddl_draft.sql](./data_dictionary_maker_checker_target_data_model_ddl_draft.sql)
- Alembic migration 设计清单：
  - [data_dictionary_maker_checker_alembic_migration_checklist.md](./data_dictionary_maker_checker_alembic_migration_checklist.md)
- ER 关系说明表：
  - [data_dictionary_maker_checker_er_relationships.md](./data_dictionary_maker_checker_er_relationships.md)

建议阅读顺序：

1. 先看本文件，理解目标模型和设计边界
2. 再看 ER 关系说明，统一实体间关系
3. 再看 DDL 草案，确认物理落表方案
4. 最后看 Alembic migration 清单，确认实施顺序
