# Data Dictionary Service Maker-Checker 开发拆分文档

## 1. 文档目的

本文基于需求截图整理，用于：

- 梳理 Data Dictionary Service 的 Maker-Checker 新需求范围
- 拆分后端、前端、数据层、校验和审计能力
- 输出可直接转 Jira 的功能点清单

说明：

- 当前已知现状：服务现阶段以 metadata 手工上传和 UI 展示为主，读操作默认无登录门槛。
- 新需求核心：为 `bulk upload` 和 `UI add/edit/delete` 增加 `maker-requester` 与 `checker-approver` 审批流。
- 登录策略按你的补充理解：仅在用户执行写操作或审批操作时校验登录；只读浏览尽量保持免登录。
- 本文对截图中未完全明确的部分做了工程化补充，并在最后列出待确认项。

## 2. 需求摘要

### 2.1 业务目标

- 为 Data Dictionary 引入 maker-checker 双人治理流程
- 支持两类变更入口：
  - 批量上传模板文件
  - UI 行级新增、编辑、删除
- 所有变更先进入待审批区，审批通过后才发布到主数据
- 支持按 tenant 维度做 AD group 权限控制
- 支持版本、历史、审计追踪

### 2.2 角色定义

- `Requester / Maker`
  - 发起数据变更
  - 可通过模板上传或 UI 行级维护提交变更
  - 可查看自己提交记录及状态
- `Approver / Checker`
  - 审核待处理变更
  - 可 approve / reject，支持批量操作
  - 不允许审批自己提交的记录
- `Viewer`
  - 仅查看审批记录和状态
  - 不具备 approve / reject 能力

### 2.3 登录与鉴权原则

- 读操作默认匿名可访问：
  - dictionary 查询
  - 搜索结果浏览
  - 页面普通展示
- 以下动作触发登录校验：
  - 上传模板文件
  - 新增记录
  - 编辑记录
  - 删除记录
  - 提交变更
  - Approver dashboard 中 approve / reject
- 登录成功后，系统要继续执行用户原本发起的动作，而不是让用户重新走一遍流程。

## 3. 端到端流程梳理

### 3.1 Bulk Upload 流程

1. Maker 下载模板
2. Maker 在模板中填写数据，并标记 `Dictionary Action` 为 `A/U/D`
3. Maker 选择上传文件
4. 系统校验用户是否已登录，且属于对应 tenant 的 Requester AD Group
5. 系统执行文件级与数据级校验
6. 校验通过后，将记录写入待审批区，状态为 `Pending`
7. Approver 在 dashboard 查看待审批记录
8. Approver 按记录或按批次 approve / reject，并填写 comments
9. 审批通过后系统发布到主表，并写入版本历史与审计日志
10. 审批拒绝后记录保留在审批区，状态改为 `Rejected`，供 Maker 查看并重新提交

### 3.2 UI Add / Edit / Delete 流程

1. 用户浏览字典明细页面
2. 用户点击 `Add`、`Edit`、`Delete` 时触发登录校验
3. 登录成功后进入可编辑态
4. 用户修改完成后点击 `Submit`
5. 系统弹出评论框，Maker 可填写 remarks
6. 系统将变更从当前主表复制到待审批区，状态设为 `Pending`
7. Approver 在 dashboard 审核并决定 approve / reject
8. 审批通过后：
   - `A`：新增记录
   - `U`：关闭旧版本并创建新版本
   - `D`：执行软删除，将主表 `Record Status` 置为 `D`
9. 审批拒绝后，主表不变，待审批记录状态为 `Rejected`

### 3.3 Approver Dashboard 流程

1. Approver 或 Viewer 进入 dashboard
2. 系统识别用户角色：
   - Approver：可查看、比较、批量 approve / reject
   - Viewer：只可查看
3. 默认展示 `Pending` tab
4. `My Requests` tab 展示当前用户提交过的记录和历史状态
5. 对于 `Update` 类记录，dashboard 需展示新旧值对比
6. Approver 操作后必须填写 comments，comments 持久化保存

## 4. 建议的数据架构

截图里提到新增 `approval table`。从实现角度，建议不要只做单表，而是拆成“请求头 + 变更明细 + 审计日志”，否则批量提交、部分通过、评论、历史查询会比较难做。

### 4.1 推荐表设计

#### A. `approval_request`

用于表示一次提交流程，适合 bulk upload 或一次 UI submit。

建议字段：

- `request_id`
- `tenant`
- `domain`
- `source_type`：`UPLOAD` / `UI`
- `submitted_by`
- `submitted_at`
- `maker_comment`
- `request_status`：`PENDING / PARTIALLY_APPROVED / APPROVED / REJECTED`
- `reviewed_by`
- `reviewed_at`
- `checker_comment`
- `source_file_name`
- `source_file_hash`

#### B. `approval_item`

用于表示每一条待审批记录。

建议字段：

- `approval_item_id`
- `request_id`
- `entity_type`：如 dataset / attribute / table name
- `business_key` 或 `primary_key_snapshot`
- `dictionary_action`：`A / U / D`
- `approval_status`：`P / A / R`
- `record_status`：`A / D`
- `requester_id`
- `approver_id`
- `requester_timestamp`
- `approver_timestamp`
- `version`
- `effective_from`
- `effective_to`
- `old_value_json`
- `new_value_json`
- `validation_errors_json`
- `maker_comment`
- `checker_comment`

#### C. `dictionary_audit_log`

用于最终审计追踪。

建议字段：

- `audit_id`
- `request_id`
- `approval_item_id`
- `tenant`
- `entity_type`
- `business_key`
- `action_type`
- `maker_id`
- `checker_id`
- `changed_at`
- `old_value_json`
- `new_value_json`
- `version`

#### D. `tenant_role_mapping` 或配置化映射

用于维护 tenant 与 AD group 的关系。

建议字段：

- `tenant`
- `domain`
- `requester_group_cn`
- `approver_group_cn`
- `viewer_group_cn`（如需要）
- `environment`

### 4.2 主表新增字段

截图中已有要求，主表或版本表至少要支持以下字段：

- `Requester_ID`
- `Approver_ID`
- `Requester_Timestamp`
- `Approver_Timestamp`
- `Version`
- `Dictionary_Action`
- `Approval_Status`
- `Record_Status`
- `Effective_From`
- `Effective_To`

### 4.3 推荐实现原则

- 主表只存“已发布/已生效”的版本
- 待审批数据只进入审批表，不直接改主表
- 如果是 `Update`，审批通过时关闭旧版本并生成新版本
- 如果是 `Delete`，采用软删除，不做物理删除
- 版本号只能递增，不能复用、不能跳号

## 5. 后端详细功能点

## 5.1 认证与权限

### BE-01 登录态校验能力

- 复用现有 LDAP/JWT 登录机制，支持前端在写操作前触发登录
- 支持 Cookie/JWT 两种方式识别会话
- 新增“当前用户是否具备当前 tenant 写权限”的接口或在现有 `/auth/me` 中返回 tenant-role 信息
- 会话过期时返回明确的 `401/403` 语义，便于前端弹登录框

### BE-02 Tenant 级 AD Group 授权

- 支持按 tenant 校验 Requester / Approver / Viewer 权限
- 权限校验不能只做全局 allowed group，必须带 tenant 维度
- 同一用户可以有多个 tenant 的不同角色
- 服务端必须校验：
  - 上传人属于对应 tenant 的 requester group
  - 审批人属于对应 tenant 的 approver group
  - requester 与 approver 不是同一个 employee id

### BE-03 权限返回模型

- 登录成功后返回：
  - 用户标识
  - employee id
  - display name
  - 可访问 tenant 列表
  - 每个 tenant 下的角色列表
- 供前端控制按钮显隐和 dashboard 权限

## 5.2 模板与批量上传

### BE-04 模板下载能力

- 更新模板下载接口
- 模板中新增 `Dictionary Action` 字段
- 模板版本需可追踪，避免前端/用户下载旧模板导致字段不匹配

### BE-05 批量上传解析与落库

- 接收上传文件
- 解析文件中的 tenant、domain、数据实体和行数据
- 计算文件 hash，用于重复文件校验
- 将解析结果转成 `approval_request + approval_item`
- 记录来源文件名、上传人、上传时间

### BE-06 批量上传校验

- 文件重复校验
- 模板结构校验
- tenant/domain 合法性校验
- Dictionary Action 取值校验，仅允许 `A/U/D`
- 数据级校验：
  - 主键或组合键重复
  - 必填字段非空
  - 特殊字符校验
  - 枚举值范围校验
  - 字段类型/长度校验
- 校验失败时返回逐行错误明细，支持前端展示

### BE-07 批量上传提交结果

- 校验成功后写入 `Pending`
- 返回 request id、成功记录数、失败记录数、错误明细
- 可选：触发通知给 approver

## 5.3 UI 行级变更与提交

### BE-08 行级 Add / Edit / Delete 暂存能力

- 支持 UI 将单条或多条新增/修改/删除记录打包提交
- 后端不直接改主表，统一先生成审批请求
- 对 `Edit` 需同时保存旧值和新值
- 对 `Delete` 需转成 `Dictionary Action = D`

### BE-09 提交接口

- 支持一次提交多条记录
- 支持 Maker comments
- 创建 `approval_request`
- 创建多条 `approval_item`
- 将状态统一置为 `Pending`

### BE-10 去重与并发控制

- 防止同一业务主键在存在 `Pending` 变更时再次提交
- 防止多个 Approver 同时审批同一批数据导致版本冲突
- 对版本递增和生效时间更新做事务控制

## 5.4 Approver Dashboard 后端能力

### BE-11 审批列表查询

- 查询 `Pending` 请求
- 查询 `My Requests`
- 查询历史请求
- 支持按 tenant、status、maker、checker、date、entity type 过滤

### BE-12 详情与差异对比

- 返回单个 request 的所有 item
- 对 `Update` 返回旧值/新值 diff 数据
- 对 `Add/Delete` 返回操作类型、主键、评论、来源

### BE-13 Approve / Reject 接口

- 支持单条审批
- 支持批量审批
- 支持单条拒绝
- 支持批量拒绝
- 审批或拒绝时必须带 checker comments

### BE-14 部分审批支持

- 如果一个 request 内多条记录可部分通过、部分拒绝，则需要：
  - item 级状态
  - request 级聚合状态
- 如果产品不需要部分审批，则可以简化为整批通过/整批拒绝
- 当前截图提到 `approve fully or partially`，建议后端按 item 级设计，避免后续返工

## 5.5 审批通过后的发布逻辑

### BE-15 `Add` 发布逻辑

- 在主表中创建新记录
- 版本初始化为 `1.0`
- `Record Status = A`
- `Effective From = 当前时间`
- `Effective To = null`

### BE-16 `Update` 发布逻辑

- 查询当前 active 版本
- 将旧版本 `Effective To` 更新为当前时间
- 新建一条新版本记录
- 版本号递增，例如 `1.0 -> 2.0`
- 新版本 `Effective From = 当前时间`
- 新版本 `Effective To = null`

### BE-17 `Delete` 发布逻辑

- 不做物理删除
- 将主表当前有效记录 `Record Status = D`
- 同时关闭当前版本有效期
- 在审批表和审计表中保留完整痕迹

## 5.6 审计、历史与搜索

### BE-18 审计日志

- 审批通过后写入 audit log
- 审计内容至少包括：
  - tenant
  - maker
  - checker
  - action type
  - old value
  - new value
  - change time
  - version

### BE-19 历史版本查询

- 支持按业务键查询所有历史版本
- 支持查看 effective from / to
- 支持区分当前生效版本与历史关闭版本

### BE-20 搜索增强（Nice to Have）

- 支持按 maker、checker、version、approval status、date 搜索
- 可作为二期功能

## 5.7 通知与帮助

### BE-21 通知能力

- 上传成功通知 approver
- reject 后通知 maker
- approve 后通知 maker
- 如果当前阶段不做邮件，可至少预留事件钩子或消息接口

### BE-22 Help 内容支撑

- 为前端 Help 文案提供 maker/checker 流程说明数据源，或由前端静态实现

## 6. 前端详细功能点

## 6.1 登录触发与页面行为

### FE-01 Lazy Login 机制

- 页面初始加载不强制登录
- 当用户点击以下按钮时触发登录判断：
  - Upload
  - Add
  - Edit
  - Delete
  - Submit
  - Approve
  - Reject
- 如果未登录：
  - 弹登录框或跳转登录页
  - 登录成功后回到原页面
  - 自动恢复用户原操作上下文

### FE-02 权限态展示

- 未登录用户只显示只读能力
- 登录后按角色显示按钮：
  - Requester 看到 upload/add/edit/delete/submit
  - Approver 看到 approve/reject
  - Viewer 只可查看
- 当用户没有当前 tenant 权限时，按钮置灰或隐藏

## 6.2 Bulk Upload 页面

### FE-03 页面文案与入口调整

- 按需求将按钮文案调整为：
  - `Download Data Dictionary Template`
  - `Upload Data Dictionary Template`

### FE-04 模板下载

- 提供模板下载入口
- 显示模板版本或更新时间

### FE-05 文件上传交互

- 选择文件后发起上传
- 展示上传进度、成功/失败提示
- 展示文件级和行级错误
- 上传成功后跳转或链接到对应 request 详情 / dashboard

### FE-06 上传结果反馈

- 成功提示 request id
- 失败时展示逐行错误
- 可选：展示“已通知 approver”提示

## 6.3 SSD 数据集页面改造

### FE-07 行级操作入口

- 每行增加 `Edit`、`Delete`
- 页面增加 `Add` 按钮
- 支持对新增行和编辑行做前端基础校验

### FE-08 新字段展示

- 在数据集页面或详情弹层展示以下字段：
  - Dictionary Action
  - Approval Status
  - Version
  - Requester
  - Approver
  - Requester Timestamp
  - Approver Timestamp
- 建议把系统自动生成字段放在“详情/历史”区域，避免主列表过宽

### FE-09 Submit 交互

- 用户完成多个改动后统一点击 `Submit`
- 弹出 comments 对话框
- 提交成功后将前端编辑态清空
- 刷新列表状态，显示这些记录已进入 `Pending`

### FE-10 重复提交与冲突提示

- 当后端返回“已有待审批记录”时，前端需明确提示用户
- 引导用户去 `My Requests` 查看状态，而不是反复提交

## 6.4 Approver Dashboard

### FE-11 Dashboard 页面结构

- 至少包含：
  - `Pending` tab
  - `My Requests` tab
- 可扩展：
  - `All`
  - `Approved`
  - `Rejected`

### FE-12 列表与筛选

- 展示 request 基本信息：
  - request id
  - tenant
  - maker
  - submit time
  - status
  - action type
- 支持筛选和搜索

### FE-13 详情与 Diff 展示

- 点击 request 查看所有变更项
- 对 `Update` 显示 old vs new 对比
- 对 `Add/Delete` 显示操作类型和关键字段

### FE-14 审批操作

- 支持单条 approve / reject
- 支持多选批量 approve / reject
- 审批时弹出 comments 输入框
- 操作成功后刷新列表状态

### FE-15 Viewer 模式

- Viewer 进入 dashboard 仅允许查看
- 不渲染 approve / reject 按钮

## 6.5 搜索、帮助、状态反馈

### FE-16 搜索增强（Nice to Have）

- 支持按 maker、checker、version、status、date 搜索

### FE-17 Help 页面更新

- 增加 maker/checker 流程说明
- 增加 bulk upload 和 UI submit 的使用说明
- 增加 reject 后如何重提的说明

### FE-18 统一消息反馈

- 登录过期提示
- 上传成功/失败提示
- 提交成功/失败提示
- 审批成功/失败提示

## 7. 核心业务规则

### 7.1 审批状态规则

- `Pending`：Maker 已提交，待审批
- `Approved`：Checker 审批通过
- `Rejected`：Checker 审批拒绝

### 7.2 记录状态规则

- `A`：Active
- `D`：Disabled

### 7.3 Action 规则

- `A`：新增
- `U`：更新
- `D`：删除/禁用

### 7.4 审批限制规则

- Checker 不能审批自己提交的 request
- 如果用户同时拥有 maker 和 approver 角色，也必须禁止 self-approval
- 一个有效记录同一时间只允许存在一个 active 版本
- `effective_to` 必须早于或等于新版本的 `effective_from`

## 8. 推荐接口清单

以下是便于前后端拆分的建议接口，不要求完全照搬：

- `POST /auth/login`
- `GET /auth/me`
- `GET /auth/permissions?tenant=...`
- `GET /dictionary/templates/latest`
- `POST /dictionary/uploads`
- `POST /dictionary/changes/submit`
- `GET /approvals/pending`
- `GET /approvals/my-requests`
- `GET /approvals/{request_id}`
- `POST /approvals/{request_id}/approve`
- `POST /approvals/{request_id}/reject`
- `POST /approvals/items/bulk-approve`
- `POST /approvals/items/bulk-reject`
- `GET /dictionary/history/{business_key}`
- `GET /dictionary/audit`

## 9. Jira 拆分建议

建议按 `Epic -> Story` 拆分，避免一个 ticket 同时覆盖 DB、API、前端、审批逻辑。

### Epic 1: 权限与登录基础

- `BE Story`：tenant 级 AD group 映射与鉴权扩展
- `BE Story`：登录态返回 tenant-role 权限模型
- `FE Story`：写操作 lazy login 与登录后回跳
- `FE Story`：基于权限的按钮显隐和禁用态

### Epic 2: 数据模型与迁移

- `BE Story`：approval request/item/audit log 表设计与 migration
- `BE Story`：主表版本字段与状态字段补充
- `BE Story`：历史版本查询基础能力

### Epic 3: Bulk Upload

- `BE Story`：模板下载接口与模板字段更新
- `BE Story`：文件上传、解析、校验、Pending 落库
- `BE Story`：重复文件检查与错误明细返回
- `FE Story`：bulk upload 页面改造
- `FE Story`：上传结果和错误展示

### Epic 4: UI Self-Service Submit

- `BE Story`：Add/Edit/Delete 暂存与 submit 接口
- `BE Story`：提交 comments 存储与并发控制
- `FE Story`：数据集页面行级 add/edit/delete
- `FE Story`：submit 对话框与 pending 状态反馈

### Epic 5: Approver Dashboard

- `BE Story`：pending/my requests/history 查询接口
- `BE Story`：diff 详情接口
- `BE Story`：approve/reject 单条与批量接口
- `FE Story`：dashboard 列表与 tab
- `FE Story`：详情对比页
- `FE Story`：批量审批与 comments 弹窗

### Epic 6: 发布、版本、审计

- `BE Story`：Add/Update/Delete 审批通过后的发布逻辑
- `BE Story`：版本递增与 effective from/to 维护
- `BE Story`：audit log 落库
- `BE Story`：禁止 self-approval 与事务一致性

### Epic 7: 体验增强和补充能力

- `FE Story`：My Requests 历史与状态查看
- `FE Story`：Help 内容更新
- `BE Story`：通知钩子或邮件通知
- `FE/BE Story`：搜索增强（nice to have）

## 10. 建议的实施顺序

1. 先做权限模型、DB 设计、审批表 migration
2. 再做 bulk upload 的后端闭环，因为这是最清晰的主流程
3. 再做 UI 行级 add/edit/delete submit
4. 再做 approver dashboard
5. 最后补 search、help、notification 和历史优化

## 11. 待确认问题

这些点如果不先确认，Jira 会比较容易拆错：

- `Viewer` 是否也是 tenant 级 AD group，还是登录后默认所有已登录用户都可看
- Approver dashboard 是否允许匿名查看
- “partial approve” 是按 request 内 item 级支持，还是只是文案描述
- bulk upload 的“duplicate file”定义是什么：
  - 同文件名
  - 同 hash
  - 同 tenant + 同 hash
- Reject 后 Maker 是否允许在原 request 上重新提交，还是必须新建 request
- 上传成功后的通知方式是否在本期实现：
  - 站内提示
  - 邮件
  - 只保留待审批列表即可
- 模板中是否需要同时暴露 `Approval Status / Version / Requester / Approver` 等系统字段，还是只暴露 `Dictionary Action`
- 现有主表是否已经有版本主键，如果没有，需要确认版本化存储方案
- 搜索增强和 Help 更新是否属于一期必做，还是二期 nice to have

## 12. 建议的 Jira Story 标题示例

- `BE | Add tenant-level requester/approver authorization for data dictionary`
- `BE | Create approval request and approval item tables for maker-checker flow`
- `BE | Implement bulk upload validation and pending staging`
- `BE | Implement approval publish logic for add/update/delete actions`
- `BE | Add audit log and version history persistence`
- `FE | Add lazy login flow for write actions`
- `FE | Update data dictionary bulk upload page for maker flow`
- `FE | Add row-level add/edit/delete and submit flow to SSD pages`
- `FE | Build approver dashboard with pending and my requests tabs`
- `FE | Add approval diff view and batch approve/reject interactions`

## 13. 完整 Task Breakdown List

本节用于把前面的 Epic / Story 再往下拆成可执行任务。建议实际建 Jira 时使用：

- `Epic -> Story -> Task -> Sub-task`
- 如果团队 Jira 层级有限，也可以直接使用：
- `Epic -> Story -> Sub-task`

建议字段：

- `Task ID`
- `Area`
- `Task`
- `Suggested Owner`
- `Depends On`
- `Deliverable`

### 13.1 Analysis / Design / Alignment

- `TD-01 | Analysis | 召开需求澄清会，确认 Phase 1 范围与 out-of-scope：viewer、notification、partial approve、search enhancement、help update 是否一期交付 | Owner: BA/PO + Tech Lead | Depends On: none | Deliverable: scope baseline`
- `TD-02 | Analysis | 明确登录策略：只读匿名、写操作登录、审批操作登录，以及登录后回跳方式 | Owner: BA/PO + FE Lead + BE Lead | Depends On: TD-01 | Deliverable: auth interaction decision`
- `TD-03 | Analysis | 确认 tenant 与 AD group 的映射来源，是配置文件、数据库表还是外部目录服务 | Owner: Architect + Security + BE Lead | Depends On: TD-01 | Deliverable: tenant-role mapping approach`
- `TD-04 | Analysis | 明确审批粒度：按 request 整批审批，还是按 item 部分审批 | Owner: BA/PO + Tech Lead | Depends On: TD-01 | Deliverable: approval granularity decision`
- `TD-05 | Analysis | 确认 bulk upload 的 duplicate file 定义：file name、hash、tenant + hash 或其他组合 | Owner: BA/PO + BE Lead | Depends On: TD-01 | Deliverable: duplicate check rule`
- `TD-06 | Analysis | 确认 reject 后 Maker 的重提方式：新 request 还是复用原 request | Owner: BA/PO + BE Lead + FE Lead | Depends On: TD-01 | Deliverable: resubmission rule`
- `TD-07 | Design | 产出 maker-checker 数据流和状态流设计图 | Owner: Solution Architect | Depends On: TD-02, TD-04, TD-06 | Deliverable: solution design`
- `TD-08 | Design | 明确版本管理规则：初始版本、更新递增、删除时版本行为、effective from/to 规则 | Owner: Architect + BE Lead | Depends On: TD-07 | Deliverable: versioning design`
- `TD-09 | Design | 明确审计范围：何时记日志、记录哪些字段、old/new value 存储格式 | Owner: Architect + Audit/Control SME + BE Lead | Depends On: TD-07 | Deliverable: audit design`
- `TD-10 | Design | 定义 API 合同草案和错误码规范，覆盖登录、上传、提交、审批、冲突、校验失败 | Owner: BE Lead + FE Lead | Depends On: TD-07 | Deliverable: API contract draft`

### 13.2 Data Model / Migration

- `TD-11 | DB | 设计 approval_request 表结构 | Owner: BE/DB Engineer | Depends On: TD-07 | Deliverable: schema draft`
- `TD-12 | DB | 设计 approval_item 表结构，包含 old_value/new_value、status、comment、version 信息 | Owner: BE/DB Engineer | Depends On: TD-07, TD-08 | Deliverable: schema draft`
- `TD-13 | DB | 设计 dictionary_audit_log 表结构 | Owner: BE/DB Engineer | Depends On: TD-09 | Deliverable: schema draft`
- `TD-14 | DB | 设计 tenant_role_mapping 表或等价配置结构 | Owner: BE/DB Engineer | Depends On: TD-03 | Deliverable: mapping schema`
- `TD-15 | DB | 评估现有主表或版本表改造方案，补充 Requester/Approver/Version/Status/Effective 字段 | Owner: BE/DB Engineer | Depends On: TD-08 | Deliverable: main table change design`
- `TD-16 | DB | 设计唯一约束和索引：pending 冲突检查、request 查询、my requests 查询、历史版本查询 | Owner: BE/DB Engineer | Depends On: TD-11, TD-12, TD-15 | Deliverable: index strategy`
- `TD-17 | DB | 编写 Alembic migration 脚本 | Owner: BE Engineer | Depends On: TD-11, TD-12, TD-13, TD-14, TD-15, TD-16 | Deliverable: migration scripts`
- `TD-18 | DB | 准备初始化或回填脚本，用于 tenant-role mapping 和主表默认值处理 | Owner: BE Engineer | Depends On: TD-17 | Deliverable: seed/backfill scripts`
- `TD-19 | DB | 评审 migration 回滚方案和数据兼容性风险 | Owner: BE Lead + DBA | Depends On: TD-17 | Deliverable: migration runbook notes`

### 13.3 Backend Auth / Authorization

- `TD-20 | BE | 扩展登录返回模型，补充 employee id、display name、tenant-role 信息 | Owner: BE Engineer | Depends On: TD-03, TD-10 | Deliverable: updated auth response`
- `TD-21 | BE | 实现 tenant 级 requester/approver/viewer 权限判定服务 | Owner: BE Engineer | Depends On: TD-03, TD-14 | Deliverable: authorization service`
- `TD-22 | BE | 为写接口增加统一鉴权中间层或 dependency，区分 401 与 403 | Owner: BE Engineer | Depends On: TD-20, TD-21 | Deliverable: protected write endpoints`
- `TD-23 | BE | 实现 self-approval 校验，禁止 maker 审批自己的 request | Owner: BE Engineer | Depends On: TD-21 | Deliverable: approval guard`
- `TD-24 | BE | 提供权限查询接口或增强 `/auth/me`，供前端做按钮显隐和页面控制 | Owner: BE Engineer | Depends On: TD-20, TD-21 | Deliverable: FE-consumable auth API`

### 13.4 Backend Bulk Upload

- `TD-25 | BE | 更新模板下载接口和模板文件，新增 Dictionary Action 字段 | Owner: BE Engineer | Depends On: TD-10 | Deliverable: template endpoint + template file`
- `TD-26 | BE | 实现上传文件接收、解析、tenant/domain 识别 | Owner: BE Engineer | Depends On: TD-25 | Deliverable: upload parser`
- `TD-27 | BE | 实现文件重复校验和模板结构校验 | Owner: BE Engineer | Depends On: TD-05, TD-26 | Deliverable: upload validation layer`
- `TD-28 | BE | 实现数据级校验：主键重复、必填、枚举、特殊字符、类型/长度 | Owner: BE Engineer | Depends On: TD-26 | Deliverable: row validation layer`
- `TD-29 | BE | 将上传结果落到 approval_request 和 approval_item，状态置为 Pending | Owner: BE Engineer | Depends On: TD-11, TD-12, TD-26, TD-27, TD-28 | Deliverable: staging persistence`
- `TD-30 | BE | 设计上传错误返回模型，支持逐行错误展示 | Owner: BE Engineer | Depends On: TD-28, TD-29 | Deliverable: error response contract`
- `TD-31 | BE | 增加上传权限校验，只允许对应 tenant 的 requester 上传 | Owner: BE Engineer | Depends On: TD-21, TD-26 | Deliverable: secured upload endpoint`

### 13.5 Backend UI Submit / Staging

- `TD-32 | BE | 设计 UI add/edit/delete 提交 payload，支持多条记录一次 submit | Owner: BE Lead + FE Lead | Depends On: TD-10 | Deliverable: submit API contract`
- `TD-33 | BE | 实现 UI submit 接口，将新增、编辑、删除统一转为 approval items | Owner: BE Engineer | Depends On: TD-12, TD-32 | Deliverable: submit API`
- `TD-34 | BE | 对 Edit 操作保存 old_value 和 new_value 快照 | Owner: BE Engineer | Depends On: TD-33 | Deliverable: diff-ready staging data`
- `TD-35 | BE | 对 Delete 操作转为软删除请求，写入 Dictionary Action = D | Owner: BE Engineer | Depends On: TD-33 | Deliverable: delete staging logic`
- `TD-36 | BE | 增加冲突校验：同一业务键存在 Pending 时禁止再次提交 | Owner: BE Engineer | Depends On: TD-16, TD-33 | Deliverable: pending conflict protection`
- `TD-37 | BE | 支持 Maker comments 持久化到 request 或 item 级别 | Owner: BE Engineer | Depends On: TD-33 | Deliverable: comment persistence`

### 13.6 Backend Approver Dashboard / Review

- `TD-38 | BE | 实现 Pending requests 列表查询接口 | Owner: BE Engineer | Depends On: TD-11, TD-12 | Deliverable: pending API`
- `TD-39 | BE | 实现 My Requests 列表查询接口 | Owner: BE Engineer | Depends On: TD-11, TD-12 | Deliverable: my requests API`
- `TD-40 | BE | 实现 request 详情接口，返回 item 明细和 comments | Owner: BE Engineer | Depends On: TD-38, TD-39 | Deliverable: approval detail API`
- `TD-41 | BE | 实现 update 类记录的 old vs new diff 组装逻辑 | Owner: BE Engineer | Depends On: TD-34, TD-40 | Deliverable: diff response model`
- `TD-42 | BE | 实现 approve 单条/批量接口 | Owner: BE Engineer | Depends On: TD-04, TD-23, TD-40 | Deliverable: approve API`
- `TD-43 | BE | 实现 reject 单条/批量接口，并要求 checker comments | Owner: BE Engineer | Depends On: TD-04, TD-23, TD-40 | Deliverable: reject API`
- `TD-44 | BE | 实现 request 级聚合状态计算：Pending、Partially Approved、Approved、Rejected | Owner: BE Engineer | Depends On: TD-04, TD-42, TD-43 | Deliverable: request status aggregation`

### 13.7 Backend Publish / Version / Audit

- `TD-45 | BE | 实现 Add 审批通过后的发布逻辑，创建首个 active 版本 | Owner: BE Engineer | Depends On: TD-15, TD-42 | Deliverable: add publish flow`
- `TD-46 | BE | 实现 Update 审批通过后的发布逻辑，关闭旧版本并创建新版本 | Owner: BE Engineer | Depends On: TD-08, TD-15, TD-42 | Deliverable: update publish flow`
- `TD-47 | BE | 实现 Delete 审批通过后的发布逻辑，执行软删除并关闭有效期 | Owner: BE Engineer | Depends On: TD-08, TD-15, TD-42 | Deliverable: delete publish flow`
- `TD-48 | BE | 为发布逻辑增加事务控制和并发保护，防止重复审批和版本冲突 | Owner: BE Engineer | Depends On: TD-45, TD-46, TD-47 | Deliverable: transactional consistency`
- `TD-49 | BE | 实现 audit log 持久化 | Owner: BE Engineer | Depends On: TD-13, TD-45, TD-46, TD-47 | Deliverable: audit persistence`
- `TD-50 | BE | 实现历史版本查询接口 | Owner: BE Engineer | Depends On: TD-15, TD-46, TD-47 | Deliverable: history API`

### 13.8 Frontend Auth / Common UX

- `TD-51 | FE | 梳理当前页面中的所有写操作入口，统一接入 lazy login 守卫 | Owner: FE Engineer | Depends On: TD-02, TD-24 | Deliverable: guarded UI actions`
- `TD-52 | FE | 实现登录弹窗或登录页跳转，并支持登录成功后回到当前页面 | Owner: FE Engineer | Depends On: TD-51 | Deliverable: login recovery flow`
- `TD-53 | FE | 实现写操作上下文恢复，例如继续 upload、打开 edit modal、继续 submit | Owner: FE Engineer | Depends On: TD-52 | Deliverable: action resume logic`
- `TD-54 | FE | 基于权限模型控制 Upload/Add/Edit/Delete/Approve/Reject 按钮显隐与禁用 | Owner: FE Engineer | Depends On: TD-24, TD-51 | Deliverable: role-based UI control`
- `TD-55 | FE | 统一处理 401/403/409/422 错误提示文案 | Owner: FE Engineer | Depends On: TD-10, TD-54 | Deliverable: global error handling`

### 13.9 Frontend Bulk Upload

- `TD-56 | FE | 更新 bulk upload 页面文案和入口布局 | Owner: FE Engineer | Depends On: TD-25 | Deliverable: updated upload page`
- `TD-57 | FE | 接入模板下载接口，展示模板版本或更新时间 | Owner: FE Engineer | Depends On: TD-25 | Deliverable: template download UI`
- `TD-58 | FE | 接入上传接口，支持文件选择、提交、进度、成功失败提示 | Owner: FE Engineer | Depends On: TD-26, TD-30, TD-31 | Deliverable: upload interaction`
- `TD-59 | FE | 展示逐行错误和校验结果摘要 | Owner: FE Engineer | Depends On: TD-30, TD-58 | Deliverable: upload error panel`
- `TD-60 | FE | 上传成功后跳转到对应 request 或 dashboard | Owner: FE Engineer | Depends On: TD-29, TD-58 | Deliverable: post-upload navigation`

### 13.10 Frontend SSD Data Set Page

- `TD-61 | FE | 在 SSD 页面增加 Add、Edit、Delete 操作入口 | Owner: FE Engineer | Depends On: TD-54 | Deliverable: row action UI`
- `TD-62 | FE | 实现行级编辑表单和新增表单 | Owner: FE Engineer | Depends On: TD-61 | Deliverable: edit/add forms`
- `TD-63 | FE | 增加前端基础校验，减少无效提交 | Owner: FE Engineer | Depends On: TD-62 | Deliverable: client validation`
- `TD-64 | FE | 实现 Submit 按钮和 comments 弹窗 | Owner: FE Engineer | Depends On: TD-32, TD-37, TD-62 | Deliverable: submit interaction`
- `TD-65 | FE | 提交成功后刷新页面状态，并提示记录已进入 Pending | Owner: FE Engineer | Depends On: TD-33, TD-64 | Deliverable: pending status feedback`
- `TD-66 | FE | 显示系统字段或在详情区显示 Version、Approval Status、Requester、Approver、Timestamp | Owner: FE Engineer | Depends On: TD-15, TD-65 | Deliverable: system metadata view`
- `TD-67 | FE | 处理“已有 Pending 记录”冲突提示，并引导用户进入 My Requests | Owner: FE Engineer | Depends On: TD-36, TD-65 | Deliverable: conflict UX`

### 13.11 Frontend Approver Dashboard

- `TD-68 | FE | 实现 dashboard 页面骨架和 tab：Pending、My Requests | Owner: FE Engineer | Depends On: TD-38, TD-39 | Deliverable: dashboard shell`
- `TD-69 | FE | 实现 Pending 列表展示、分页、筛选和状态展示 | Owner: FE Engineer | Depends On: TD-38, TD-68 | Deliverable: pending list UI`
- `TD-70 | FE | 实现 My Requests 列表展示和历史状态查看 | Owner: FE Engineer | Depends On: TD-39, TD-68 | Deliverable: my requests UI`
- `TD-71 | FE | 实现 request 详情抽屉或详情页，展示 item 明细和 comments | Owner: FE Engineer | Depends On: TD-40, TD-68 | Deliverable: approval detail UI`
- `TD-72 | FE | 实现 old vs new diff 视图 | Owner: FE Engineer | Depends On: TD-41, TD-71 | Deliverable: diff UI`
- `TD-73 | FE | 实现单条 approve/reject 操作和 comments 弹窗 | Owner: FE Engineer | Depends On: TD-42, TD-43, TD-71 | Deliverable: single review action UI`
- `TD-74 | FE | 实现批量 approve/reject 操作 | Owner: FE Engineer | Depends On: TD-42, TD-43, TD-69 | Deliverable: bulk review UI`
- `TD-75 | FE | 实现 viewer 模式，只允许查看不允许操作 | Owner: FE Engineer | Depends On: TD-21, TD-68 | Deliverable: viewer-safe dashboard`

### 13.12 Notification / Help / Search Enhancements

- `TD-76 | BE | 设计并实现审批结果通知钩子，至少预留接口或事件 | Owner: BE Engineer | Depends On: TD-42, TD-43 | Deliverable: notification hook`
- `TD-77 | FE | 更新 Help 内容，补充 maker/checker 流程说明 | Owner: FE Engineer | Depends On: TD-01 | Deliverable: help content update`
- `TD-78 | BE | 如纳入一期，实现按 maker/checker/version/date/status 的查询增强接口 | Owner: BE Engineer | Depends On: TD-50 | Deliverable: search API enhancement`
- `TD-79 | FE | 如纳入一期，实现高级搜索 UI | Owner: FE Engineer | Depends On: TD-78 | Deliverable: search filter UI`

### 13.13 Testing / QA / UAT

- `TD-80 | QA | 编写 test scenario 清单，覆盖 bulk upload、UI submit、approve、reject、history、audit、permission 边界 | Owner: QA Lead | Depends On: TD-10 | Deliverable: QA test matrix`
- `TD-81 | BE | 为 auth 和 authorization 增加单元测试 | Owner: BE Engineer | Depends On: TD-20, TD-21, TD-22, TD-23 | Deliverable: unit tests`
- `TD-82 | BE | 为 bulk upload 解析和校验增加单元测试 | Owner: BE Engineer | Depends On: TD-26, TD-27, TD-28, TD-29 | Deliverable: unit tests`
- `TD-83 | BE | 为 publish/version/audit 增加单元测试 | Owner: BE Engineer | Depends On: TD-45, TD-46, TD-47, TD-49, TD-50 | Deliverable: unit tests`
- `TD-84 | BE | 增加 API/integration tests，覆盖 submit -> approve/reject -> publish 全链路 | Owner: BE Engineer | Depends On: TD-33, TD-42, TD-43, TD-45, TD-46, TD-47 | Deliverable: integration tests`
- `TD-85 | FE | 增加前端交互测试，覆盖 lazy login、upload、submit、dashboard、diff | Owner: FE Engineer | Depends On: TD-52, TD-58, TD-64, TD-72, TD-74 | Deliverable: FE tests`
- `TD-86 | QA | 执行 SIT/UAT，用真实 tenant-role 样本验证权限边界 | Owner: QA + Business UAT | Depends On: TD-81, TD-82, TD-83, TD-84, TD-85 | Deliverable: UAT sign-off`

### 13.14 Deployment / Release / Rollout

- `TD-87 | DevOps/BE | 准备配置项和 secrets 清单，例如 AD group mapping、template version、feature flags | Owner: DevOps + BE Lead | Depends On: TD-03, TD-25 | Deliverable: config checklist`
- `TD-88 | DevOps/BE | 准备 DB migration 执行计划和回滚预案 | Owner: DevOps + DBA + BE Lead | Depends On: TD-17, TD-19 | Deliverable: migration runbook`
- `TD-89 | FE/BE | 评估是否使用 feature flag 控制 maker-checker 能力按 tenant 灰度开启 | Owner: FE Lead + BE Lead | Depends On: TD-01, TD-87 | Deliverable: rollout strategy`
- `TD-90 | DevOps | 部署到 SIT/UAT/Prod 并验证 smoke test | Owner: DevOps + QA | Depends On: TD-86, TD-88, TD-89 | Deliverable: environment rollout`
- `TD-91 | BA/PO + Tech Lead | 组织 go-live checklist review，确认监控、支持人、回滚联系人、已知限制 | Owner: PO + Tech Lead | Depends On: TD-90 | Deliverable: go-live approval`

### 13.15 推荐 Jira 建单方式

如果你想控制 ticket 数量，建议不要把上面 90+ 项全部建成 Story。更合理的方式是：

- `Epic`：按第 9 节划分
- `Story`：按能力模块划分，例如“Bulk Upload Backend”“Approver Dashboard Frontend”
- `Task/Sub-task`：按本节 `TD-xx` 粒度拆分

推荐最小可执行拆法：

- 每个后端 Story 控制在 `3-6` 个 task
- 每个前端 Story 控制在 `3-5` 个 task
- DB migration 单独一个 Story，不要混进业务逻辑 Story
- 测试和 UAT 至少单独建一个 Story 或 task，不要默认并入开发 ticket
- 部署和 rollout 单独建 task，避免上线准备无人认领
