# Data Dictionary Service Maker-Checker ER Relationship Notes

## 1. 目的

本文档用于说明基于当前 Data Dictionary Service 模型扩展后的实体关系，帮助前后端开发、后端 reviewer、DBA 和测试统一理解：

- 哪些表是主数据表
- 哪些表是审批暂存表
- 哪些表是历史版本表
- 哪些关系是强外键
- 哪些关系是逻辑关联

对应设计文档：

- 目标模型设计：[data_dictionary_maker_checker_target_data_model.md](./data_dictionary_maker_checker_target_data_model.md)
- PostgreSQL DDL 草案：[data_dictionary_maker_checker_target_data_model_ddl_draft.sql](./data_dictionary_maker_checker_target_data_model_ddl_draft.sql)

命名说明：

- 物理表 `table_entity` 在本次业务语义中等同于 `dataset`
- 物理表 `attribute_entity` 表示 dataset 下的字段定义

## 2. 实体清单

| 实体 | 类型 | 主键 | 角色 | 备注 |
| --- | --- | --- | --- | --- |
| `domain_entity` | master | `id` | Domain 主数据 | 现有表 |
| `tenant_entity` | master | `id` | Tenant 主数据 | 现有表 |
| `table_entity` | current | `id` | 当前已发布 dataset | 现有表，业务上等于 dataset |
| `attribute_entity` | current | `id` | 当前已发布 attribute | 现有表 |
| `approval_request` | workflow header | `request_id` | 一次 maker 提交的请求头 | 新增 |
| `tenant_role_mapping` | access control | `mapping_id` | tenant 级角色到 AD group 的映射 | 新增 |
| `table_entity_pending` | pending | `pending_id` | 待审批 dataset 版本 | 新增 |
| `attribute_entity_pending` | pending | `pending_id` | 待审批 attribute 版本 | 新增 |
| `table_entity_history` | history | `history_id` | dataset 历史版本 | 新增 |
| `attribute_entity_history` | history | `history_id` | attribute 历史版本 | 新增 |

## 3. 分层视角

可以把整个模型分成 5 层：

1. 主数据层：
   - `domain_entity`
   - `tenant_entity`
2. 当前发布层：
   - `table_entity`
   - `attribute_entity`
3. 审批请求层：
   - `approval_request`
4. 审批暂存层：
   - `table_entity_pending`
   - `attribute_entity_pending`
5. 历史版本层：
   - `table_entity_history`
   - `attribute_entity_history`

权限映射层独立存在：

- `tenant_role_mapping`

## 4. 核心关系总览表

| No. | Source | Relation | Target | 类型 | 关系说明 |
| --- | --- | --- | --- | --- | --- |
| 1 | `tenant_entity.domain_id` | `->` | `domain_entity.id` | 物理 FK | 一个 tenant 属于一个 domain |
| 2 | `table_entity.domain_id` | `->` | `domain_entity.id` | 物理 FK | 一个 dataset 属于一个 domain |
| 3 | `table_entity.tenant_unique_id` | `->` | `tenant_entity.id` | 物理 FK | 一个 dataset 属于一个 tenant |
| 4 | `attribute_entity.table_id` | `->` | `table_entity.id` | 物理 FK | 一个 attribute 属于一个 dataset |
| 5 | `attribute_entity.domain_id` | `=>` | `domain_entity.id` | 逻辑关联 | 由 metadata 派生，通常应与所属 dataset 一致 |
| 6 | `attribute_entity.tenant_unique_id` | `=>` | `tenant_entity.id` | 逻辑关联 | 由 metadata 派生，通常应与所属 dataset 一致 |
| 7 | `approval_request.domain_id` | `->` | `domain_entity.id` | 物理 FK | 一次审批请求归属于一个 domain |
| 8 | `approval_request.tenant_unique_id` | `->` | `tenant_entity.id` | 物理 FK | 一次审批请求归属于一个 tenant |
| 9 | `tenant_role_mapping.domain_id` | `->` | `domain_entity.id` | 物理 FK | 角色映射归属于 domain |
| 10 | `tenant_role_mapping.tenant_unique_id` | `->` | `tenant_entity.id` | 物理 FK | 角色映射归属于 tenant |
| 11 | `table_entity.latest_request_id` | `->` | `approval_request.request_id` | 物理 FK | 当前 dataset 最近一次来源请求 |
| 12 | `attribute_entity.latest_request_id` | `->` | `approval_request.request_id` | 物理 FK | 当前 attribute 最近一次来源请求 |
| 13 | `table_entity_pending.request_id` | `->` | `approval_request.request_id` | 物理 FK | pending dataset 归属于某次请求 |
| 14 | `table_entity_pending.target_table_id` | `->` | `table_entity.id` | 物理 FK | Update/Delete 指向现有 dataset；Add 可为空 |
| 15 | `attribute_entity_pending.request_id` | `->` | `approval_request.request_id` | 物理 FK | pending attribute 归属于某次请求 |
| 16 | `attribute_entity_pending.target_attribute_id` | `->` | `attribute_entity.id` | 物理 FK | Update/Delete 指向现有 attribute；Add 可为空 |
| 17 | `attribute_entity_pending.table_id` | `=>` | `table_entity.id` | 逻辑关联 | 指向所属 dataset；Add 场景可能先关联 pending 中的新 dataset |
| 18 | `table_entity_history.table_id` | `->` | `table_entity.id` | 物理 FK | dataset 历史版本属于某个 current 逻辑实体 |
| 19 | `table_entity_history.source_request_id` | `->` | `approval_request.request_id` | 物理 FK | 历史版本由哪次请求产生 |
| 20 | `attribute_entity_history.attribute_id` | `->` | `attribute_entity.id` | 物理 FK | attribute 历史版本属于某个 current 逻辑实体 |
| 21 | `attribute_entity_history.source_request_id` | `->` | `approval_request.request_id` | 物理 FK | 历史版本由哪次请求产生 |
| 22 | `attribute_entity_history.table_id` | `=>` | `table_entity.id` | 逻辑关联 | 便于按 dataset 维度查询 attribute 历史 |

说明：

- `->` 表示物理外键关系
- `=>` 表示逻辑关联关系

## 5. 关系解读

## 5.1 Domain 与 Tenant

- 一个 `domain_entity` 可以拥有多个 `tenant_entity`
- `tenant_entity` 是 tenant 维度的主数据源
- maker/checker 的 tenant 权限控制最终都落在 `tenant_unique_id`

## 5.2 Dataset 与 Attribute

- 一个 `table_entity` 可以拥有多个 `attribute_entity`
- `attribute_entity.table_id` 是最关键的层级外键
- `attribute_entity` 上的 `domain_id / tenant_unique_id` 属于冗余派生字段，用于检索和过滤，不应成为主关系来源

## 5.3 Approval Request 与 Pending

- 一次 `approval_request` 可以包含多个 dataset pending 项
- 一次 `approval_request` 也可以包含多个 attribute pending 项
- 因此 `approval_request : pending item` 是 `1 : N`
- bulk upload 和 UI submit 都共享同一套 request header

## 5.4 Current 与 History

- 一个 current dataset 在生命周期内会对应多个 history 版本
- 一个 current attribute 在生命周期内也会对应多个 history 版本
- 因此：
  - `table_entity : table_entity_history = 1 : N`
  - `attribute_entity : attribute_entity_history = 1 : N`
- current 表只保留当前发布版本
- history 表保留旧版本

## 5.5 Current 与 Pending

- 对同一条 current 记录，任一时刻最多只允许存在一个 `approval_status = 'P'` 的 pending 版本
- 这就是 `table_entity_pending_target_pending_uq` 与 `attribute_entity_pending_target_pending_uq` 的设计目的
- 它们用于防止同一条记录在未审批完成前被重复提交

## 5.6 Tenant 与 Role Mapping

- 一个 tenant 可以映射多个角色类型
- 当前设计中角色类型包括：
  - `REQUESTER`
  - `APPROVER`
  - `VIEWER`
- 通过 `(tenant_unique_id, role_type)` 唯一约束保证每个 tenant 的每种角色只对应一条活动配置

## 6. 生命周期映射

## 6.1 浏览当前发布数据

查询来源：

- `table_entity`
- `attribute_entity`

说明：

- UI 默认展示 current published 数据
- 不直接查询 pending 表

## 6.2 Maker 提交变更

落库路径：

1. 创建 `approval_request`
2. 写入 `table_entity_pending`
3. 写入 `attribute_entity_pending`

说明：

- 此时 current 表不更新
- 所有变更都先进入 pending

## 6.3 Checker 审批通过

处理路径：

1. 读取对应 pending 记录
2. 若为 Update，则先把原 current 快照写入 history
3. 更新或新增 current 记录
4. 更新 pending 状态为 approved
5. 更新 `approval_request` 汇总状态

## 6.4 Checker 驳回

处理路径：

1. pending 保留
2. pending 行状态改为 rejected
3. `approval_request` 更新为 `REJECTED` 或 `PARTIALLY_APPROVED`
4. current 表不变

## 7. 版本关系说明

版本链路如下：

- current 表保存当前版本
- history 表保存已经关闭的历史版本
- pending 表保存待审批版本

对于 Update：

1. 当前 `table_entity.version_seq = N`
2. maker 提交后，`table_entity_pending.target_version_seq = N + 1`
3. checker 通过后：
   - 原 current 版本写入 history，保留 `version_seq = N`
   - 新 current 版本写入 `version_seq = N + 1`

对于 Add：

1. pending 版本号目标值为 `1`
2. 审批通过后 current 首版本为 `1.0`

对于 Delete：

- 当前设计默认解释为禁用当前记录，而不是生成新的删除版本
- 如果后续业务要求 delete 也形成显式新版本，需要额外扩展模型和审批落库规则

## 8. 推荐的 ASCII 关系图

```text
domain_entity
    |
    +--< tenant_entity
            |
            +--< tenant_role_mapping
            |
            +--< approval_request
            |       |
            |       +--< table_entity_pending
            |       |       |
            |       |       +--> table_entity (target on update/delete)
            |       |
            |       +--< attribute_entity_pending
            |               |
            |               +--> attribute_entity (target on update/delete)
            |
            +--< table_entity
                    |
                    +--< attribute_entity
                    |
                    +--< table_entity_history
                    |
                    +-- latest_request_id --> approval_request

attribute_entity
    |
    +--< attribute_entity_history
    |
    +-- latest_request_id --> approval_request
```

## 9. 开发实现注意点

- 前端口径统一使用 `dataset`，避免把业务对象叫成 `table`
- 后端数据库对象仍使用现有物理命名 `table_entity`
- API DTO 中建议显式区分：
  - `datasetId`
  - `tableEntityId`
  - `requestId`
  - `pendingId`
  - `historyId`
- 对 `attribute_entity_pending.table_id` 的处理要特别小心：
  - 若 dataset 也是新增且尚未审批，不能简单依赖 current `table_entity.id`
  - bulk upload 场景可能需要通过 request 内部的临时映射关系关联 dataset 和 attribute

## 10. 最终建议

如果要让前后端对同一套关系有一致理解，建议评审时按下面顺序看：

1. 先看本 ER 文档，统一表之间的角色与边界
2. 再看目标模型设计，理解为什么这样拆表
3. 最后看 DDL 草案和 migration checklist，确认实施方案

下一步如果继续往下落，可以补的产物有：

- 一张更适合贴到 Confluence 的 ER summary 表
- 一张按 API 维度整理的 request/response 字段映射表
