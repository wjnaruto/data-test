# Data Dictionary Service Maker-Checker Alembic Migration Checklist

## 1. 目的

本文档用于把目标数据模型设计转成可执行的 Alembic migration 方案，供后端开发、DBA 和 reviewer 使用。

对应交付物：

- 目标模型设计：[data_dictionary_maker_checker_target_data_model.md](./data_dictionary_maker_checker_target_data_model.md)
- PostgreSQL DDL 草案：[data_dictionary_maker_checker_target_data_model_ddl_draft.sql](./data_dictionary_maker_checker_target_data_model_ddl_draft.sql)

本文档不替代 DDL 草案，而是回答下面几个实际实施问题：

- migration 应该拆成几步
- 哪些步骤属于 schema change，哪些属于 data backfill
- 哪些约束应该延后增加，降低锁表和失败风险
- Alembic 里哪些对象适合用 `op.*`，哪些更适合用 `op.execute`
- 升级、校验、回滚各自应该怎么做

## 2. 迁移范围

本次 migration 覆盖的对象如下：

- 新表：
  - `approval_request`
  - `tenant_role_mapping`
  - `table_entity_pending`
  - `attribute_entity_pending`
  - `table_entity_history`
  - `attribute_entity_history`
- 现有表增量改造：
  - `table_entity`
  - `attribute_entity`
- 新视图：
  - `approval_dashboard_v`

不在本次 migration 范围内的内容：

- 业务接口改造
- 审批服务逻辑
- 通知机制
- 单独的 immutable audit ledger 表

说明：

- 现阶段审计能力主要依赖 `approval_request + pending/history/current` 的组合信息。
- 如果后续业务确认必须提供“不可变更的独立审计台账”，建议另开一轮模型扩展。

## 3. 迁移总体策略

建议采用“分阶段、小步提交、先 schema 后 backfill、最后加约束”的方式：

1. 先创建完全独立的新表，不影响当前读路径。
2. 再给 `table_entity` 和 `attribute_entity` 增加新字段，但第一阶段保持可空。
3. 对存量 current 数据做一次性 backfill，把旧数据补成 maker-checker 兼容格式。
4. backfill 验证通过后，再补约束、外键和索引。
5. 最后创建 dashboard view。

核心原则：

- 避免把“建表、回填、加非空、加重索引”塞进同一个 revision。
- 能延后校验的约束尽量延后，比如 `CHECK ... NOT VALID` 后再 `VALIDATE CONSTRAINT`。
- 高成本索引需要评估是否使用 `CONCURRENTLY`；如果使用，则不能放在默认事务里执行。
- 数据回填失败时，优先通过恢复策略或重新执行 revision 解决，不建议依赖复杂 downgrade。

## 4. 推荐 Revision 拆分

| Revision | 建议名称 | 目标 | 主要对象 | 备注 |
| --- | --- | --- | --- | --- |
| `mc_001` | create_request_and_role_tables | 先落审批头表和权限映射表 | `approval_request`, `tenant_role_mapping` | 完全新增，风险最低 |
| `mc_002` | add_governance_columns_to_current_tables | 给 current published 表增加治理字段 | `table_entity`, `attribute_entity` | 字段先保持 nullable |
| `mc_003` | backfill_current_published_records | 回填现有数据的版本和状态 | `table_entity`, `attribute_entity` | 纯数据迁移 |
| `mc_004` | add_constraints_and_indexes_to_current_tables | 在 current 表上补 FK、check、index | `table_entity`, `attribute_entity` | 建议在 backfill 后执行 |
| `mc_005` | create_pending_tables | 落地审批暂存表 | `table_entity_pending`, `attribute_entity_pending` | 支撑 maker submit |
| `mc_006` | create_history_tables | 落地历史版本表 | `table_entity_history`, `attribute_entity_history` | 支撑 approve 后归档 |
| `mc_007` | create_dashboard_view | 统一审批 dashboard 读模型 | `approval_dashboard_v` | 可独立回滚 |
| `mc_008` | seed_role_mapping_optional | 可选初始化租户 AD group 映射 | `tenant_role_mapping` | 视环境决定是否执行 |

## 5. 每个 Revision 的实施清单

## 5.1 `mc_001` 创建 `approval_request` 与 `tenant_role_mapping`

### Upgrade 内容

- 创建 `approval_request`
- 创建 `tenant_role_mapping`
- 创建主键、唯一约束、基础 check constraint
- 创建基础查询索引

### Alembic 实现建议

- 优先使用 `op.create_table`
- 普通 btree index 可使用 `op.create_index`
- `CHECK` 约束如果不需要 `NOT VALID`，可直接在 `create_table` 中定义

### 验证项

- 两张新表可正常创建
- `tenant_role_mapping` 的 `(tenant_unique_id, role_type)` 唯一约束生效
- `approval_request` 的状态和值域约束生效

### Downgrade 建议

- 直接 `drop_table` 即可

## 5.2 `mc_002` 给 current published 表增加治理字段

### Upgrade 内容

给 `table_entity` 增加：

- `requester_id`
- `approver_id`
- `requester_ts`
- `approver_ts`
- `version_seq`
- `version_label`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

给 `attribute_entity` 增加：

- `requester_id`
- `approver_id`
- `requester_ts`
- `approver_ts`
- `version_seq`
- `version_label`
- `dictionary_action`
- `approval_status`
- `record_status`
- `effective_from`
- `effective_to`
- `latest_request_id`

### Alembic 实现建议

- 普通列使用 `op.add_column`
- `version_label` 建议使用 `sa.Computed`
- 此阶段不要立即设置 `NOT NULL`
- 此阶段不要立即增加复杂 `CHECK`
- `latest_request_id` 外键建议放到下一个 revision 再补

### 验证项

- 字段存在
- 旧数据不报错
- 旧查询路径仍可运行

### Downgrade 建议

- 仅在尚未执行 backfill 前允许 `drop_column`
- 一旦后续 revision 已依赖这些字段，不建议通过 downgrade 删除

## 5.3 `mc_003` 回填 current published 数据

### 回填目标

把历史上已经存在的 current 数据补齐成 maker-checker 能识别的“已批准当前版本”。

### `table_entity` 回填规则

- `version_seq = 1`
- `dictionary_action = 'A'`，如果当前 `deleted = true` 则置为 `'D'`
- `approval_status = 'A'`
- `record_status = 'A'`，如果当前 `deleted = true` 则置为 `'D'`
- `effective_from = createdat 对应时间`
- `effective_to = NULL`

### `attribute_entity` 回填规则

- `version_seq = 1`
- `dictionary_action = 'A'`，如果当前 `deleted = true` 则置为 `'D'`
- `approval_status = 'A'`
- `record_status = 'A'`，如果当前 `deleted = true` 则置为 `'D'`
- `effective_from = createdat 对应时间`
- `effective_to = NULL`

### 时间戳处理建议

当前模型中的 `createdat` 可能是秒级 Unix time，也可能是毫秒级 Unix time。

建议使用与 DDL 草案一致的判断逻辑：

- 若 `createdat > 100000000000`，按毫秒时间戳转换
- 否则按秒时间戳转换
- 若 `createdat` 缺失，则用 migration 执行时刻或系统约定初始时间回填

### Alembic 实现建议

- 使用 `op.execute()` 执行显式 `UPDATE` 语句
- 如果数据量较大，建议单独一个 revision 只做 backfill
- 如果需要分批回填，建议在 migration 外部执行受控 SQL job，不要在 Alembic 里写复杂循环

### 验证 SQL 建议

```sql
SELECT COUNT(*) FROM public.table_entity WHERE version_seq IS NULL;
SELECT COUNT(*) FROM public.table_entity WHERE dictionary_action IS NULL;
SELECT COUNT(*) FROM public.table_entity WHERE approval_status IS NULL;
SELECT COUNT(*) FROM public.table_entity WHERE record_status IS NULL;
SELECT COUNT(*) FROM public.table_entity WHERE effective_from IS NULL;

SELECT COUNT(*) FROM public.attribute_entity WHERE version_seq IS NULL;
SELECT COUNT(*) FROM public.attribute_entity WHERE dictionary_action IS NULL;
SELECT COUNT(*) FROM public.attribute_entity WHERE approval_status IS NULL;
SELECT COUNT(*) FROM public.attribute_entity WHERE record_status IS NULL;
SELECT COUNT(*) FROM public.attribute_entity WHERE effective_from IS NULL;
```

### Downgrade 建议

- 不建议对 backfill 做逐行回滚
- 如需回退，建议回退到 migration 前数据库快照

## 5.4 `mc_004` 补 current 表约束与索引

### Upgrade 内容

- `latest_request_id -> approval_request.request_id` 外键
- `version_seq / dictionary_action / approval_status / record_status / effective_from` 设为 `NOT NULL`
- 增加 check constraint：
  - `dictionary_action IN ('A', 'U', 'D')`
  - `approval_status IN ('A', 'P', 'R')`
  - `record_status IN ('A', 'D')`
  - `effective_to IS NULL OR effective_to >= effective_from`
- 增加 current 表索引

### Alembic 实现建议

- `NOT NULL` 使用 `op.alter_column`
- FK 使用 `op.create_foreign_key`
- 需要 `NOT VALID` 的 check constraint 使用 `op.execute`
- 普通索引可以 `op.create_index`
- trigram GIN 索引建议 `op.execute("CREATE INDEX ... USING gin ... gin_trgm_ops")`

### 生产环境注意事项

- 如果索引数据量很大，需要评估是否使用 `CREATE INDEX CONCURRENTLY`
- `CONCURRENTLY` 不能运行在 Alembic 默认事务中
- 如果必须用 `CONCURRENTLY`，应使用 autocommit block 或拆成 DBA 执行脚本

### 验证项

- 所有新约束已存在
- 无约束违反数据
- 关键 dashboard 查询可以命中新增索引

## 5.5 `mc_005` 创建 pending 表

### Upgrade 内容

- 创建 `table_entity_pending`
- 创建 `attribute_entity_pending`
- 创建 request FK、target FK、状态约束、唯一 pending 约束
- 创建全文搜索和 dashboard 检索索引

### Alembic 实现建议

- 继续保持与现有模型一致的 `jsonb + generated columns`
- generated columns 使用 `sa.Computed`
- trigram 索引继续使用 `op.execute`
- 部分唯一索引使用 `postgresql_where`

### 设计要点

- pending 表保存“待审批版本”，不是 current 表的副本
- `target_*_id` 在 Add 场景可以为空，在 Update/Delete 场景必须指向现有 current 记录
- `approval_status` 初始值为 `P`

### 验证项

- 可以插入 Add 类型 pending 记录
- 可以插入 Update/Delete 类型 pending 记录
- 同一个目标 current 记录不能同时存在多个 `PENDING` pending 版本

## 5.6 `mc_006` 创建 history 表

### Upgrade 内容

- 创建 `table_entity_history`
- 创建 `attribute_entity_history`
- 创建版本唯一约束
- 创建按实体和版本倒序查询的索引

### 设计要点

- history 表保存“旧版本快照”
- 审批通过后，旧 current 记录先归档到 history，再写入新的 current 状态
- `effective_to` 在 history 表必须非空，表示该版本已结束

### 验证项

- `(table_id, version_seq)` 唯一
- `(attribute_id, version_seq)` 唯一
- 所有 history 行都满足 `effective_to >= effective_from`

## 5.7 `mc_007` 创建 dashboard view

### Upgrade 内容

- 创建或替换 `approval_dashboard_v`
- 将 dataset pending 与 attribute pending 做 `UNION ALL`

### 设计要点

- view 只负责统一读模型，不承载业务规则
- 业务过滤仍由应用层控制，例如 tenant 权限、我的申请、待审批标签页

### 验证项

- view 可正常查询
- 能同时看到 dataset 和 attribute 两类待审批项
- view 字段能满足 dashboard UI 的最小展示需求

## 5.8 `mc_008` 可选初始化 tenant role mapping

### 适用场景

- 目标环境已知每个 tenant 对应的 Requester / Approver / Viewer AD group
- 需要在首发前一次性写入权限映射

### 实现建议

- 如果环境差异大，优先用独立 seed 脚本，不要写进通用 migration
- 如果必须写进 Alembic，请把数据源做成可审计的静态清单

## 6. Alembic 代码层实现建议

## 6.1 推荐使用 `op.*` 的场景

- `op.create_table`
- `op.add_column`
- `op.alter_column`
- `op.create_foreign_key`
- `op.create_index`
- `op.drop_table`
- `op.drop_index`

## 6.2 推荐使用 `op.execute()` 的场景

- 大段 backfill SQL
- `CHECK ... NOT VALID`
- `VALIDATE CONSTRAINT`
- `CREATE EXTENSION IF NOT EXISTS pg_trgm`
- trigram GIN 索引
- `CREATE OR REPLACE VIEW`

## 6.3 推荐的 Revision 文件组织

建议 1 个 revision 只做 1 类变更：

- 新表
- 当前表增列
- 回填
- 约束与索引
- 视图

不建议：

- 一个 revision 同时做建表、回填、加非空和大索引

## 7. 回滚策略

本次迁移更适合采用“前向修复 + 备份恢复”的回滚策略，而不是依赖复杂 downgrade。

建议如下：

- `mc_001`、`mc_005`、`mc_006`、`mc_007` 可提供相对标准的 downgrade
- `mc_003` 数据回填 revision 不建议做逐行回滚
- 一旦 current 表治理字段已经被应用层依赖，`mc_002` 和 `mc_004` 的 downgrade 风险较高

推荐的生产回退策略：

1. 变更前做数据库快照或备份
2. 先在预发验证回填耗时和索引创建耗时
3. 生产出现严重问题时，优先通过备份恢复而不是强行 downgrade

## 8. 上线前检查清单

- 确认 `pg_trgm` 扩展可安装
- 确认当前 `table_entity` / `attribute_entity` 数据量
- 确认 `createdat` 的单位分布是否一致
- 确认是否存在脏数据会违反未来约束
- 确认是否需要 `CREATE INDEX CONCURRENTLY`
- 确认是否需要先停写或限制变更窗口
- 确认 `tenant_role_mapping` 是否由 migration 初始化

## 9. 上线后校验清单

- 新表和视图均已创建
- current 表新增字段均存在
- current 表历史数据 backfill 完成
- 所有 required 约束已生效
- dashboard view 可查到数据
- 现有只读查询路径未受影响

建议执行的最小校验 SQL：

```sql
SELECT COUNT(*) AS table_missing_version
FROM public.table_entity
WHERE version_seq IS NULL;

SELECT COUNT(*) AS attribute_missing_version
FROM public.attribute_entity
WHERE version_seq IS NULL;

SELECT COUNT(*) AS table_invalid_window
FROM public.table_entity
WHERE effective_to IS NOT NULL
  AND effective_to < effective_from;

SELECT COUNT(*) AS attribute_invalid_window
FROM public.attribute_entity
WHERE effective_to IS NOT NULL
  AND effective_to < effective_from;

SELECT COUNT(*) AS pending_dataset_tables
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'table_entity_pending';

SELECT COUNT(*) AS history_attribute_tables
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name = 'attribute_entity_history';
```

## 10. 最终建议

建议把这次数据库迁移按下面顺序组织到开发计划中：

1. 先评审目标模型与 DDL 草案
2. 再冻结 revision 切分方式
3. 先在开发环境跑通 `mc_001 ~ mc_007`
4. 在预发环境重点验证 `mc_003` backfill 和大索引耗时
5. 最后再进入生产发布窗口

如果后续需要继续往下走，下一步最合适的产物是：

- 基于本清单生成 Alembic revision 文件骨架
- 把 DDL 草案拆成每个 revision 对应的 upgrade/downgrade 脚本模板
