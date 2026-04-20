# Data Dictionary Service Maker-Checker 正式开发文档

## 1. 文档信息

- 文档目的：基于原始需求文档，形成一份可供前后端开发、测试、Tech Lead、BA/PO 共用的正式开发文档
- 适用范围：Data Dictionary Service 的 Maker-Checker 一期需求
- 目标读者：Frontend、Backend、QA、Tech Lead、BA/PO
- 来源文档：
  - `docs/data_dictionary_requirements_raw_transcription.md`
  - `docs/data_dictionary_requirements_bilingual.md`
  - `docs/data_dictionary_maker_checker_breakdown.md`

## 2. 需求 Summary

### 2.1 背景

当前 Data Dictionary Service 的主要能力是：

- 手工上传各个 producer tenant 的 metadata
- 在 UI 上展示数据字典内容
- 读操作默认无登录门槛

新增需求的核心目标是：

- 为 Data Dictionary 引入 Maker-Checker 治理流程
- 让数据字典的新增、更新、删除和批量上传都先进入审批流程，再发布到主数据
- 通过 tenant 级 AD group 做访问控制
- 引入版本、历史和审计能力

### 2.2 业务目标

- 提高数据字典条目的准确性、完整性和治理可追踪性
- 让 Maker 与 Checker 的职责边界清晰化
- 让自助维护能力可控，而不是直接改生产可见数据
- 建立可审计、可回溯、可版本化的数据字典管理流程

### 2.3 角色定义

- `Anonymous / Read-only User`
  - 仅浏览和搜索，不执行写操作
- `Requester / Maker`
  - 发起批量上传或 UI 行级维护
  - 提交变更供审批
  - 查看自己提交的请求和审批结果
- `Approver / Checker`
  - 审核 Pending 请求
  - 批准或拒绝变更
  - 不能审批自己提交的请求
- `Viewer`
  - 只能查看审批记录、状态和历史
  - 不具备 approve/reject 能力

### 2.4 一期范围

- tenant 级 AD group 权限控制
- 写操作触发登录，读操作尽量保持匿名访问
- Bulk upload 的模板下载、上传、校验、暂存、审批
- UI 行级 Add / Edit / Delete / Submit
- Approver Dashboard
- 审批通过后的发布逻辑
- 版本管理、历史管理、审计日志
- 基础搜索增强、Help 内容增强

### 2.5 建议作为二期或待确认范围

- 邮件通知是否一期实现
- 高级搜索是否一期实现
- `partial approval` 是否一期真正落地
- `Viewer` 是否必须单独定义 tenant 级 AD group

## 3. End-to-End Flow Summary

### 3.1 只读浏览与登录触发流程

1. 用户打开 Data Dictionary 页面。
2. 用户浏览数据字典内容、查询和搜索时，不强制要求登录。
3. 当用户点击 `Upload`、`Add`、`Edit`、`Delete`、`Submit`、`Approve`、`Reject` 时，系统检查登录态。
4. 若未登录，前端弹出登录窗口或跳转登录页。
5. 登录成功后，恢复用户原本操作上下文，继续执行原始动作。

### 3.2 Bulk Upload 流程

1. Maker 下载最新模板。
2. Maker 在模板中填写数据，并为每条记录设置 `Dictionary Action = A/U/D`。
3. Maker 点击上传按钮，系统校验登录态和 tenant 级 Requester 权限。
4. 后端执行文件级校验和数据级校验。
5. 校验通过后，系统生成审批请求并将记录写入审批暂存区，状态为 `Pending`。
6. Approver 在 Dashboard 的 `Pending` tab 查看待处理请求。
7. Approver 审核后执行 approve 或 reject，并填写 comments。
8. 若 approve，系统发布到主表，生成版本和审计日志。
9. 若 reject，主表不变，审批记录状态更新为 `Rejected`。

### 3.3 UI 行级 Add / Edit / Delete 流程

1. 用户进入 SSD 数据集页面。
2. 用户点击 `Add`、`Edit`、`Delete` 时触发登录与权限校验。
3. 用户完成行级变更后点击 `Submit`。
4. 系统弹出 comments 对话框，Maker 可填写备注。
5. 后端将变更写入审批暂存区，不直接改主表。
6. Approver 在 Dashboard 中查看对应请求。
7. Approver 审核并 approve / reject。
8. 若 approve：
   - `A`：新增一条新的 active 记录
   - `U`：关闭旧版本并创建新版本
   - `D`：执行软删除，将 `Record Status` 设为 `D`
9. 若 reject：主表保持不变，请求和明细记录状态更新为 `Rejected`

### 3.4 Approver Dashboard 流程

1. Approver 或 Viewer 打开 Approver Dashboard。
2. 默认展示 `Pending` tab。
3. `My Requests` tab 用于查看自己提交过的请求及其状态。
4. 对于 `Update` 类型记录，页面展示新旧值对比。
5. Approver 可执行单条或批量 approve / reject。
6. 所有审批动作都需要记录 checker comments。

### 3.5 发布、版本、历史、审计流程

1. 审批通过后，系统根据 `Dictionary Action` 决定发布方式。
2. 对于 `Add`：
   - 只有在 `校验成功 + Approver 批准` 后，系统才为记录分配正式版本号
   - 主表新增记录
   - 版本号初始化为 `1.0`
   - `Effective From = 当前审批通过时间`
   - `Effective To = null`
3. 对于 `Update`：
   - 只有在 `校验成功 + Approver 批准` 后，系统才生成新的正式版本
   - 当前 active 版本的 `Effective To` 设为当前审批通过时间，用于关闭旧版本
   - 生成新版本记录，版本号按顺序递增，例如 `1.0 -> 2.0`
   - 新版本的 `Effective From` 设为同一个当前审批通过时间
   - 必须保证旧版本与新版本在时间区间上无重叠
4. 对于 `Delete`：
   - 原始需求明确要求做软删除/禁用，不做物理删除
   - 默认解释为：更新当前 active 记录的 `Record Status = D`
   - 建议同时关闭该版本的有效期，即设置 `Effective To = 当前审批通过时间`
   - 当前需求没有明确要求 Delete 产生一个新的版本号，因此一期不默认把 Delete 设计成“生成新版本”；如业务希望 Delete 也形成新版本，需要单独确认
5. 所有审批通过的变更写入 audit log。

### 3.6 状态流转摘要

| 场景 | Request Status | Approval Item Status | Main Table 状态 |
| --- | --- | --- | --- |
| Maker 提交成功 | `PENDING` | `P` | 不变 |
| Checker 全部批准 | `APPROVED` | `A` | 发布变更 |
| Checker 全部拒绝 | `REJECTED` | `R` | 不变 |
| Checker 部分批准 | `PARTIALLY_APPROVED` | `A/R` 混合 | 仅发布已批准项 |

## 4. 核心业务规则与设计原则

### 4.1 权限规则

- 读操作尽量匿名可访问
- 写操作必须登录
- 权限控制按 tenant 维度判断，而不是全局角色
- Approver 必须来自对应 tenant 的 Approver AD group
- Requester 必须来自对应 tenant 的 Requester AD group
- Requester 与 Approver 不能是同一人

### 4.2 数据与状态规则

- `Dictionary Action`
  - `A` = Add
  - `U` = Update
  - `D` = Delete / Disable
- `Approval Status`
  - `P` = Pending
  - `A` = Approved
  - `R` = Rejected
- `Record Status`
  - `A` = Active
  - `D` = Disabled

### 4.3 版本规则

#### 4.3.1 正式版本号生成时点

- 正式版本号不是在 Maker 提交时生成，而是在 `后端校验成功且经 Approver 批准` 后生成
- Pending 审批数据可以带候选版本信息，也可以为空，但不能视为正式发布版本

#### 4.3.2 Add 的版本规则

- 新记录在首次审批通过时生成第一个正式版本
- 初始版本号固定从 `1.0` 开始
- `Effective From = 审批通过并发布的时间`
- `Effective To = null`

#### 4.3.3 Update 的版本规则

- 仅当 Update 被审批通过后，才生成下一正式版本
- 新版本号必须在上一版本基础上顺序递增，例如 `1.0 -> 2.0 -> 3.0`
- 版本号不能复用，不能跳号
- 在生成新版本之前，必须先关闭旧版本：
  - 旧版本 `Effective To = 当前审批通过时间`
  - 新版本 `Effective From = 当前审批通过时间`

#### 4.3.4 时间有效性规则

- `Effective From` 表示版本开始生效的时间点
- `Effective To` 表示版本失效或关闭的时间点
- 需求要求旧版本 `Effective To` 与新版本 `Effective From` 不能重叠
- 为了满足“同一时间点交接且无重叠”，建议系统采用半开区间语义：
  - 版本有效区间按 `[Effective From, Effective To)` 解释
  - 这样当旧版本 `Effective To = 新版本 Effective From` 时，不构成时间重叠

#### 4.3.5 Delete 的版本解释

- 原始需求文本只明确规定：
  - Delete 是软删除 / Disable
  - 审批通过后将 `Record Status` 更新为 `D`
- 原始需求没有明确写明 Delete 必须生成一个新的版本号
- 因此一期建议按以下规则实现：
  - Delete 不生成新的正式版本号
  - 直接将当前 active 记录置为 `D`
  - 建议同时设置 `Effective To = 当前审批通过时间`，形成生命周期闭环
- 如果业务后续希望 Delete 也以“禁用版本”形式产生新版本，需要补充需求后再扩展

#### 4.3.6 历史记录管理规则

- 历史版本和旧版本需要长期可追溯
- 历史数据可采用以下两类方案：
  - 方案 A：单一版本化表，同时保存 current + history
  - 方案 B：当前主表 + 专用历史表
- 原始需求允许 solution team 推荐方案，因此正式需求不强绑某一种物理设计
- 一期建议优先选择“易于保证版本顺序、易于查询历史、易于控制当前 active 记录”的实现方式

#### 4.3.7 技术建议

- 不建议把版本号仅作为字符串直接运算
- 建议内部维护一个连续递增的数值型 revision 序号，再向外展示为 `1.0`、`2.0`、`3.0`
- 这样更容易保证“不复用、不跳号、顺序递增”的约束

### 4.4 数据治理规则

- 审批前不允许直接更新主表
- Delete 必须是软删除，不做物理删除
- 所有审批通过后的变更都必须写入审计日志
- 当相同业务键已有 Pending 请求时，不应允许重复提交

### 4.5 技术实现建议

- 数据模型建议拆分为 `approval_request`、`approval_item`、`dictionary_audit_log`
- 前端按钮显隐依赖用户 tenant-role 信息
- Dashboard 需支持 diff 视图，否则 Update 场景难以审核
- 后端审批、版本切换、主表发布必须在事务中完成
- 版本切换必须在同一事务中完成以下动作：关闭旧版本、创建新版本、写审计日志
- 系统需要显式保证版本时间区间无重叠

### 4.6 数据模型与接口影响摘要

#### 建议新增或调整的数据表

| 对象 | 类型 | 用途 |
| --- | --- | --- |
| `approval_request` | 新增表 | 表示一次提交请求，记录来源、提交人、请求状态、评论等 |
| `approval_item` | 新增表 | 表示 request 下的单条待审批记录，保存 action、old/new value、审批状态等 |
| `dictionary_audit_log` | 新增表 | 记录审批通过后的最终审计轨迹 |
| `tenant_role_mapping` | 新增表或配置 | 维护 tenant 与 AD group 映射关系 |
| 发布数据表（主表/版本表） | 调整 | 增加 `Requester_ID`、`Approver_ID`、`Version`、`Approval_Status`、`Record_Status`、`Effective_From`、`Effective_To`，并支持 current 与 history 管理 |

#### 版本化存储建议

| 方案 | 描述 | 优点 | 风险/代价 |
| --- | --- | --- | --- |
| 方案 A：单版本化发布表 | 同一张发布表同时保存当前版本和历史版本，通过 `Record_Status`、`Effective_From`、`Effective_To` 区分 | 结构统一，历史查询自然 | 当前查询要明确过滤 active 版本 |
| 方案 B：当前主表 + 历史表 | 主表仅保存当前 active 数据，历史版本写入独立 history table | 当前查询更轻量 | 发布逻辑、迁移和历史查询更复杂 |

建议：

- 一期优先选择能最稳定满足“顺序版本、无时间重叠、历史可查询”的方案
- 如果当前系统读流量远高于历史查询，且已有主表结构固定，`方案 B` 可考虑
- 如果更看重版本一致性和实现简洁度，`方案 A` 更容易落地

#### 建议后端 API 范围

| API 分类 | 建议接口 | 用途 |
| --- | --- | --- |
| Auth | `POST /auth/login` | 登录 |
| Auth | `GET /auth/me` | 获取当前用户与 tenant-role 信息 |
| Template | `GET /dictionary/templates/latest` | 下载最新模板 |
| Upload | `POST /dictionary/uploads` | 上传模板文件并生成审批请求 |
| Submit | `POST /dictionary/changes/submit` | 提交 UI 行级变更 |
| Approval Query | `GET /approvals/pending` | 查询 Pending 请求 |
| Approval Query | `GET /approvals/my-requests` | 查询 My Requests |
| Approval Query | `GET /approvals/{request_id}` | 查询 request 详情和 diff |
| Approval Action | `POST /approvals/{request_id}/approve` | 执行 approve |
| Approval Action | `POST /approvals/{request_id}/reject` | 执行 reject |
| History | `GET /dictionary/history/{business_key}` | 查询版本历史 |
| Audit/Search | `GET /dictionary/audit` | 查询审计数据或扩展搜索 |

## 5. 功能点编号目录

| 功能点编号 | 功能点名称 | 说明 |
| --- | --- | --- |
| `FP-01` | Tenant Role & Auth Foundation | tenant 级角色识别、鉴权、登录态返回 |
| `FP-02` | Lazy Login & Action Resume | 写操作登录触发、登录后恢复操作 |
| `FP-03` | Template & Bulk Upload Entry | 模板下载、上传入口、上传页改造 |
| `FP-04` | Bulk Upload Validation & Staging | 文件解析、校验、Pending 暂存 |
| `FP-05` | SSD Row-Level Maintenance | 行级新增、编辑、删除、提交 |
| `FP-06` | Approval Dashboard Query & View | Pending / My Requests / Detail / Diff |
| `FP-07` | Approval Actions & Comments | Approve / Reject / Batch Actions / Comments |
| `FP-08` | Publish / Version / History / Audit | 发布、版本、历史、审计 |
| `FP-09` | Help / Search / Notification | Help、基础搜索、通知钩子 |
| `FP-10` | Testing / Rollout Readiness | 测试、迁移、上线准备 |

## 6. 需求与对应功能点总览表

说明：

- `Suggested Jira` 列为建议 Jira Story 名称或编号规则，用于建单时参考
- `Actual Jira ID` 列建议在建单后由 PM / Tech Lead 补齐
- `Status` 列用于后续周会或 sprint 跟踪

| Req ID | 需求项 | 目标 | 功能点编号 | 前端详细开发点 | 后端详细开发点 | Suggested FE Jira | Suggested BE Jira | Suggested QA/OPS Jira | Actual Jira ID | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `REQ-01` | Tenant 级身份与权限控制 | 确保只有合法角色能在对应 tenant 执行写与审批动作 | `FP-01` `FP-02` | `FE-01` `FE-02` `FE-03` | `BE-01` `BE-02` `BE-03` `BE-04` `BE-21` | `DDS-MC-FE-01 Lazy login and permission gating` | `DDS-MC-BE-01 Tenant auth and role service` | `DDS-MC-QA-01 Auth and role regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-02` | 模板下载与批量上传入口改造 | 提供标准模板和受控上传入口 | `FP-03` | `FE-04` `FE-05` `FE-06` | `BE-05` `BE-06` | `DDS-MC-FE-02 Bulk upload page enhancement` | `DDS-MC-BE-02 Template API and file intake` | `DDS-MC-QA-02 Upload entry validation` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-03` | Bulk Upload 校验与 Pending 暂存 | 在审批前拦截无效数据，并把有效数据写入审批区 | `FP-04` | `FE-06` `FE-07` | `BE-07` `BE-08` `BE-09` `BE-10` `BE-11` | `DDS-MC-FE-02 Bulk upload page enhancement` | `DDS-MC-BE-03 Bulk upload validation and staging` | `DDS-MC-QA-03 Bulk upload validation regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-04` | SSD 行级 Add/Edit/Delete/Submit | 支持自助维护并通过审批流提交 | `FP-05` | `FE-08` `FE-09` `FE-10` `FE-11` | `BE-12` `BE-13` `BE-14` `BE-15` | `DDS-MC-FE-03 SSD row maintenance and submit UX` | `DDS-MC-BE-04 SSD submit API and conflict control` | `DDS-MC-QA-04 SSD submit regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-05` | Approver Dashboard 列表与详情 | 让 Approver / Viewer 能查看 pending、history 和请求详情 | `FP-06` | `FE-12` `FE-13` `FE-14` | `BE-16` `BE-17` `BE-18` | `DDS-MC-FE-04 Approver dashboard UI` | `DDS-MC-BE-05 Approval dashboard query APIs` | `DDS-MC-QA-05 Dashboard query regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-06` | Approve / Reject / Batch / Comments | 支持单条和批量审批，并保留审批意见 | `FP-07` | `FE-15` `FE-16` `FE-17` | `BE-19` `BE-20` `BE-21` | `DDS-MC-FE-04 Approver dashboard UI` | `DDS-MC-BE-06 Approve reject action APIs` | `DDS-MC-QA-06 Approval action regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-07` | 发布、版本、历史、审计 | 审批通过后分配正式版本号并安全发布：Add 从 `1.0` 开始，Update 顺序递增且无时间重叠，Delete 默认执行禁用并关闭有效期，同时保证历史与审计可回溯 | `FP-08` | `FE-14` `FE-18` | `BE-22` `BE-23` `BE-24` `BE-25` `BE-26` `BE-27` | `DDS-MC-FE-05 Status and history visibility` | `DDS-MC-BE-07 Publish version history audit` | `DDS-MC-QA-07 Publish and audit regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-08` | Help、Search、Notification Hook | 补齐使用说明和基础可用性能力 | `FP-09` | `FE-19` `FE-20` | `BE-28` `BE-29` | `DDS-MC-FE-06 Help and search enhancement` | `DDS-MC-BE-08 Search and notification hook` | `DDS-MC-QA-08 Help/search regression` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |
| `REQ-09` | 测试、迁移、上线准备 | 保证变更可以安全发布并可回滚 | `FP-10` | `FE-21` | `BE-30` `BE-31` | `DDS-MC-FE-07 FE regression support` | `DDS-MC-BE-09 Migration and rollout support` | `DDS-MC-QA-09 E2E UAT and rollout` | `FE:TBD`<br>`BE:TBD`<br>`QA:TBD` | `Not Started` |

## 7. 前端详细开发点

### 7.1 认证与权限

`FE-01` 写操作拦截与 lazy login 入口统一化

- 所有写入口接入统一登录检查
- 覆盖 `Upload`、`Add`、`Edit`、`Delete`、`Submit`、`Approve`、`Reject`

`FE-02` 登录成功后的页面回跳与操作恢复

- 登录成功后返回原页面
- 自动恢复用户操作上下文，例如继续上传、继续提交、继续审批

`FE-03` tenant-role 感知的按钮显隐和禁用态

- 未登录用户只展示只读能力
- Requester、Approver、Viewer 三类用户按 tenant 控制 UI 能力

### 7.2 Bulk Upload 页面

`FE-04` 模板下载入口与文案更新

- 页面按钮文案更新为 `Download Data Dictionary Template`
- 显示模板版本或更新时间

`FE-05` 上传入口与交互改造

- 文件选择、上传按钮、上传进度、成功/失败提示
- 上传成功后跳转到 request 或 dashboard

`FE-06` 上传结果与错误展示

- 展示 request id
- 展示逐行错误
- 展示文件级校验失败信息

`FE-07` 上传后列表可见性与状态反馈

- 上传成功后可在 approver dashboard 中看到记录
- Maker 可以看到自己上传结果

### 7.3 SSD 数据集页面

`FE-08` 行级 Add / Edit / Delete 操作入口

- 增加 `Add` 按钮
- 行内增加 `Edit`、`Delete`

`FE-09` 行级编辑表单和新增表单

- 单行可编辑表单
- 新增行录入表单

`FE-10` 前端基础校验

- 必填校验
- 基础格式校验
- 尽量提前阻止无效提交

`FE-11` Submit 交互与 Maker comments

- `Submit` 按钮
- comments 对话框
- 提交成功后清空编辑态并刷新状态

### 7.4 Approver Dashboard

`FE-12` Dashboard 页面骨架

- `Pending` tab
- `My Requests` tab
- 可扩展的历史视图入口

`FE-13` 列表、筛选与状态展示

- request id、tenant、maker、submit time、status、action type
- 支持基础 filter/search

`FE-14` 请求详情和字段展示

- 请求详情页或抽屉
- 显示业务字段、系统字段、审批状态、版本信息

`FE-15` old vs new diff 视图

- Update 类型必须显示新旧值对比

`FE-16` 单条 approve / reject 交互

- 选择记录后 approve / reject
- 填写 checker comments

`FE-17` 批量 approve / reject 交互

- 支持多选
- 批量操作后刷新列表

`FE-18` 历史、状态和审计可见性

- 用户能够查看自己的请求状态
- 适当展示已批准、已拒绝、待处理结果
- 历史版本视图需明确区分“当前生效版本”与“历史关闭版本”

### 7.5 增强项与交付支持

`FE-19` Help 内容更新

- 增加 Maker / Checker 流程说明

`FE-20` Search 增强与统一消息反馈

- 按 maker / checker / version / date / status 基础搜索
- 统一 401 / 403 / 409 / 422 错误反馈

`FE-21` 前端测试支持与上线配合

- 覆盖关键交互的回归测试
- 配合 SIT / UAT / rollout 验证

## 8. 后端详细开发点

### 8.1 认证、权限、角色模型

`BE-01` tenant 级角色映射能力

- 支持 Requester / Approver / Viewer 的 tenant 级权限判断

`BE-02` 扩展登录返回模型

- 返回 employee id、display name、tenant-role 信息

`BE-03` 写接口统一鉴权拦截

- 对写操作接口启用统一鉴权
- 明确区分 `401` 与 `403`

`BE-04` self-approval 防护

- 禁止 Requester 审批自己提交的 request

### 8.2 模板与上传入口

`BE-05` 模板下载接口与模板版本管理

- 输出带 `Dictionary Action` 字段的新模板

`BE-06` 上传入口与文件接收

- 接收上传文件
- 提取 tenant / domain / source metadata

### 8.3 Bulk Upload 校验与暂存

`BE-07` 文件 hash 和重复文件检测

- 支持 duplicate file 检测

`BE-08` 模板结构与文件级校验

- 模板完整性
- 必需列检查

`BE-09` 数据级校验

- 主键/组合键重复
- 必填字段
- 特殊字符
- 枚举值范围
- 类型和长度

`BE-10` 批量上传错误模型

- 返回逐行错误
- 返回文件级错误

`BE-11` 批量上传 Pending 暂存

- 生成 request 记录
- 生成 approval item 记录

### 8.4 UI Submit 与冲突控制

`BE-12` UI Submit API

- 接收新增、编辑、删除的变更 payload

`BE-13` old/new snapshot 生成

- 为 Update 记录保留旧值与新值

`BE-14` Delete 转软删除请求

- 将删除请求标准化为 `Dictionary Action = D`

`BE-15` Pending 冲突控制

- 同一业务键在 Pending 时不允许重复提交

### 8.5 Dashboard 查询与审批接口

`BE-16` Pending 列表 API

- 支持按 tenant、status、date 等基础过滤

`BE-17` My Requests 列表 API

- 返回当前用户已提交请求及状态

`BE-18` Request Detail / Diff API

- 返回 item 明细
- Update 返回 old/new diff

`BE-19` Approve API

- 单条 approve
- 批量 approve

`BE-20` Reject API

- 单条 reject
- 批量 reject

`BE-21` comments 与 request/item 状态聚合

- 保存 maker/checker comments
- 聚合 request 级状态

### 8.6 数据发布、版本、历史、审计

`BE-22` Add 发布逻辑

- 仅在审批通过后创建正式发布记录
- 创建新记录
- 初始化版本为 `1.0`
- 设置 `Effective From = 审批通过时间`
- 设置 `Effective To = null`

`BE-23` Update 发布逻辑

- 查找当前 active 版本
- 将旧版本 `Effective To` 设置为当前审批通过时间
- 创建新版本
- 新版本号按顺序递增，例如 `1.0 -> 2.0`
- 新版本 `Effective From = 当前审批通过时间`
- 需要保证旧版本与新版本时间区间无重叠

`BE-24` Delete 发布逻辑

- 按原始需求执行软删除 / Disable
- 默认不生成新版本号
- 更新当前 active 记录的 `Record Status = D`
- 建议同时关闭该记录的有效期，即设置 `Effective To = 当前审批通过时间`

`BE-25` 事务控制与并发保护

- 审批动作与发布动作必须一致性完成
- 需要同时保护：
  - 顺序版本分配
  - 有效期切换
  - 审计日志写入
  - 防止并发审批导致版本跳号或时间重叠

`BE-26` 审计日志持久化

- 写入 tenant、maker、checker、action、old/new value、timestamp

`BE-27` 历史版本查询

- 按 business key 查询历史版本
- 支持区分 current 与 historical versions
- 支持后续扩展为 dedicated history table 或 partition 策略

### 8.7 增强项与交付支持

`BE-28` Search API 增强

- 支持 maker / checker / version / date / status 搜索

`BE-29` Help / Notification Hook 支撑

- 提供帮助内容支撑或通知钩子

`BE-30` 数据模型、迁移与索引

- approval tables
- audit log
- main table 新字段
- 索引、唯一约束

`BE-31` 上线支持与回滚准备

- migration runbook
- rollout 支持
- 回滚准备

## 9. 建议 Jira Ticket 拆分与跟踪方式

### 9.1 建议的 Epic

| Epic 编号 | Epic 名称 | 覆盖范围 |
| --- | --- | --- |
| `EPIC-01` | Access and Authorization | `REQ-01` |
| `EPIC-02` | Bulk Upload | `REQ-02` `REQ-03` |
| `EPIC-03` | SSD Self-Service Maintenance | `REQ-04` |
| `EPIC-04` | Approver Dashboard | `REQ-05` `REQ-06` |
| `EPIC-05` | Publish, Version and Audit | `REQ-07` |
| `EPIC-06` | Search, Help and Notification | `REQ-08` |
| `EPIC-07` | Test, Migration and Rollout | `REQ-09` |

### 9.2 建议的 Story

| 建议 Jira 编号 | 类型 | Story 名称 | 建议 Owner | 覆盖开发点 |
| --- | --- | --- | --- | --- |
| `DDS-MC-FE-01` | FE Story | Lazy login and permission gating | FE | `FE-01` `FE-02` `FE-03` |
| `DDS-MC-BE-01` | BE Story | Tenant auth and role service | BE | `BE-01` `BE-02` `BE-03` `BE-04` |
| `DDS-MC-FE-02` | FE Story | Bulk upload page enhancement | FE | `FE-04` `FE-05` `FE-06` `FE-07` |
| `DDS-MC-BE-02` | BE Story | Template API and file intake | BE | `BE-05` `BE-06` |
| `DDS-MC-BE-03` | BE Story | Bulk upload validation and staging | BE | `BE-07` `BE-08` `BE-09` `BE-10` `BE-11` |
| `DDS-MC-FE-03` | FE Story | SSD row maintenance and submit UX | FE | `FE-08` `FE-09` `FE-10` `FE-11` |
| `DDS-MC-BE-04` | BE Story | SSD submit API and conflict control | BE | `BE-12` `BE-13` `BE-14` `BE-15` |
| `DDS-MC-FE-04` | FE Story | Approver dashboard UI | FE | `FE-12` `FE-13` `FE-14` `FE-15` `FE-16` `FE-17` |
| `DDS-MC-BE-05` | BE Story | Approval dashboard query APIs | BE | `BE-16` `BE-17` `BE-18` |
| `DDS-MC-BE-06` | BE Story | Approve reject action APIs | BE | `BE-19` `BE-20` `BE-21` |
| `DDS-MC-FE-05` | FE Story | Status and history visibility | FE | `FE-18` |
| `DDS-MC-BE-07` | BE Story | Publish version history audit | BE | `BE-22` `BE-23` `BE-24` `BE-25` `BE-26` `BE-27` |
| `DDS-MC-FE-06` | FE Story | Help and search enhancement | FE | `FE-19` `FE-20` |
| `DDS-MC-BE-08` | BE Story | Search and notification hook | BE | `BE-28` `BE-29` |
| `DDS-MC-BE-09` | BE Story | Migration and rollout support | BE | `BE-30` `BE-31` |
| `DDS-MC-QA-01` | QA Story | Auth and role regression | QA | `REQ-01` |
| `DDS-MC-QA-02` | QA Story | Upload and staging regression | QA | `REQ-02` `REQ-03` |
| `DDS-MC-QA-03` | QA Story | SSD submit and approval regression | QA | `REQ-04` `REQ-05` `REQ-06` |
| `DDS-MC-QA-04` | QA Story | Publish audit history regression | QA | `REQ-07` |
| `DDS-MC-QA-05` | QA Story | UAT and rollout verification | QA | `REQ-08` `REQ-09` |

### 9.3 Jira 跟踪建议

- 每个 `REQ-xx` 至少映射到一个 FE Story 或一个 BE Story
- 所有 `FE-xx` / `BE-xx` 开发点必须被某个 Story 覆盖
- 建议在 Jira 中增加字段：
  - `Req ID`
  - `Feature Point ID`
  - `Owner`
  - `Dependency`
  - `Target Sprint`
  - `Status`
- 建议每周同步一次覆盖矩阵，检查是否仍有 `TBD` Jira 未落地

## 10. 交付检查项

### 10.1 Frontend DoD

- 写操作全部接入登录拦截
- 页面权限显隐符合 tenant-role 规则
- Bulk upload、SSD submit、Dashboard、Diff、Approve/Reject 均可正常操作
- 关键错误码有清晰提示

### 10.2 Backend DoD

- 所有写接口具备 tenant 级权限校验
- Bulk upload 和 UI submit 都写入审批区而不是直改主表
- 审批通过后的主表更新、版本切换、审计日志在事务中完成
- 支持历史查询和基本的审批查询

### 10.3 QA / UAT DoD

- 完成 auth / upload / submit / approve / reject / publish / audit 全链路回归
- 覆盖 self-approval、防重复提交、软删除、版本递增、diff 展示等边界场景
- UAT 签字后才能进入生产发布窗口

## 11. 待确认项

| 编号 | 待确认项 | 影响范围 |
| --- | --- | --- |
| `TBD-01` | `Viewer` 是否必须定义为 tenant 级角色 | 权限模型、Dashboard |
| `TBD-02` | `partial approval` 是一期必做还是仅保留架构兼容 | Dashboard、审批状态模型 |
| `TBD-03` | duplicate file 的定义是文件名、hash 还是 tenant + hash | 上传校验 |
| `TBD-04` | Maker comments 是否必填 | FE Submit / BE 校验 |
| `TBD-05` | reject 后是复用原 request 还是新建 request | 请求模型、UI 体验 |
| `TBD-06` | 邮件通知是否在一期实现 | Notification |
| `TBD-07` | 搜索增强和 Help 更新是否一期上线 | 范围和排期 |
| `TBD-08` | 当前主表是否已经支持版本化主键 | 数据模型与 migration |
| `TBD-09` | Delete 是否只禁用当前版本，还是也需要生成一个新的“禁用版本” | 版本策略、发布逻辑 |
| `TBD-10` | 历史版本采用单版本表还是当前表 + 历史表 | 数据模型、查询性能、migration |
