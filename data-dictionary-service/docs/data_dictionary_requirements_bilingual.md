# Data Dictionary Requirement Specifications - Bilingual Version

Note:

- English content below is transcribed from the screenshots.
- Chinese content is a direct translation for reference.

## 1. Enhancements for Maker (Requester) and Checker (Approver) process / Maker（Requester）与 Checker（Approver）流程增强

### English

In the Data Mesh environment, the accuracy, consistency, and governance of data assets are critical to business success. To further strengthen these foundations, we are enhancing the Data Mesh's data dictionary (DD) and expanding self-service capabilities through a structured maker and checker process.

This process offers two distinct approval paths:

1. Editable Self-Service UI: Makers can directly update entries via the user interface, which are then reviewed and approved by Checkers.
2. Bulk Upload: Makers submit multiple records in bulk, with Checkers responsible for reviewing and approving these entries.

This enhancement establishes a more structured and collaborative workflow, ensuring that every data dictionary entry is thoroughly validated prior to release. Makers are empowered to provide comprehensive, context-rich definitions, while Checkers independently assess entries for compliance, quality, and alignment with organizational standards.

By formalizing this process, we aim to:

- Increase trust in data assets by ensuring all entries are accurate and up to date.
- Promote accountability and transparency through clear roles and responsibilities.
- Accelerate data discovery and usage by providing stakeholders with reliable, well-governed data definitions.

Ultimately, this enhancement supports our commitment to robust data governance, cross-domain collaboration, and agile business decision-making within the Data Mesh framework.

### 中文

在 Data Mesh 环境中，数据资产的准确性、一致性和治理能力对业务成功至关重要。为进一步夯实这些基础，我们正在增强 Data Mesh 的数据字典（DD），并通过结构化的 maker / checker 流程扩展自助服务能力。

该流程提供两条不同的审批路径：

1. 可编辑自助式 UI：Maker 可以直接通过用户界面更新条目，随后由 Checker 进行审核和批准。
2. 批量上传：Maker 可以批量提交多条记录，由 Checker 负责审核并批准这些条目。

这一增强建立了更结构化、更具协作性的工作流，确保每一条数据字典记录在发布之前都经过充分验证。Maker 能够提供更完整、上下文更丰富的定义，而 Checker 则独立地从合规性、质量以及与组织标准的一致性角度对条目进行评估。

通过将该流程正式化，我们希望实现：

- 通过确保所有条目准确且保持最新，提升对数据资产的信任。
- 通过清晰的角色与职责划分，提升问责性和透明度。
- 通过为相关方提供可靠、治理良好的数据定义，加速数据发现与使用。

最终，该增强方案将支持我们在 Data Mesh 框架下对稳健数据治理、跨域协作以及敏捷业务决策的承诺。

## 2. User Journey for bulk upload and edit record using UI / 通过 UI 进行批量上传与记录编辑的用户旅程

### 2.1 Bulk upload / 批量上传

### English

1. Identify the need for a new or updated data dictionary entry. Download the relevant template for data dictionary submission.
2. Preparation of file for upload and review to ensure accuracy and completeness.
3. Submission: Upload the completed entry to the Data Dictionary (DD) services.
4. Approver (Checker) Review: The checker reviews the submitted entry for quality, compliance, and alignment with standards.
5. Feedback or Approval:
   a. If issues are found, the checker rejects the change and notifies the maker for revision, efficient notification mechanism to be adapted.
   b. If approved, the checker versions the data dictionary entry.
6. Release: The approved data dictionary version is released to users.
7. Completion: The process concludes.

### 中文

1. 识别新增或更新数据字典条目的需求，并下载相应的数据字典提报模板。
2. 准备待上传文件，并进行检查以确保其准确性和完整性。
3. 提交：将填写完成的条目上传至 Data Dictionary（DD）服务。
4. Approver（Checker）审核：Checker 对提交的条目进行质量、合规性以及与标准一致性的审查。
5. 反馈或批准：
   a. 如果发现问题，Checker 拒绝该变更，并通知 Maker 进行修订；高效的通知机制需要后续适配。
   b. 如果批准，Checker 会为该数据字典条目生成版本。
6. 发布：经批准的数据字典版本发布给用户。
7. 完成：流程结束。

### 2.2 Update/Delete/Add using UI / 通过 UI 进行更新、删除、新增

### English

1. Update/ Add/ Delete of records in data mesh
2. Submit changes
3. Approver (Checker) Review: The checker reviews the submitted entry for quality, compliance, and alignment with standards.
4. Feedback or Approval:
   a. If issues are found, the checker rejects the change and notifies the maker for revision.
   b. If approved, approved record will be created as new version and if old record exists then it will be closed.
5. Release: The approved data dictionary version is released to users.
6. Completion: The process concludes.

### 中文

1. 在 data mesh 中对记录执行更新 / 新增 / 删除。
2. 提交变更。
3. Approver（Checker）审核：Checker 对提交的条目进行质量、合规性以及与标准一致性的审查。
4. 反馈或批准：
   a. 如果发现问题，Checker 拒绝该变更，并通知 Maker 进行修订。
   b. 如果批准，则经批准的记录会以新版本形式创建；如果旧记录存在，则旧记录会被关闭。
5. 发布：经批准的数据字典版本发布给用户。
6. 完成：流程结束。

## 3. Access Management using AD groups / 使用 AD 组进行访问管理

### English

- New AD or access control groups to be created to support Requester (Maker) and Approver (checker) governance control at tenant level
- This is applicable to all environments
- Follow the enterprise standard naming convention for these group names

| S. No | Domain | Tenant | Access control |
| --- | --- | --- | --- |
| 1 | Fund Administration | Geneva | Requester AD Group / Approver AD group |
| 2 | Fund Administration | Icon | Requester AD Group / Approver AD group |
| 3 | Fund Administration | MF/MS | Requester AD Group / Approver AD group |
| 4 | Fund Administration | pControl | Requester AD Group / Approver AD group |
| 5 | Custody | Custody Unity | Requester AD Group / Approver AD group |
| 6 | Transfer Agency | GTAP | Requester AD Group / Approver AD group |
| 7 | Treasury | Treasury | Requester AD Group / Approver AD group |
| 8 | Middle office | HSS trade flow | Requester AD Group / Approver AD group |
| 9 | Middle office | Markit EDM | Requester AD Group / Approver AD group |
| 10 | Middle office | Calypso | Requester AD Group / Approver AD group |
| 10 | Securities lending | Globalone | Requester AD Group / Approver AD group |

### 中文

- 需要创建新的 AD 组或访问控制组，以在 tenant 层面支持 Requester（Maker）和 Approver（Checker）的治理控制。
- 该要求适用于所有环境。
- 这些组名需要遵循企业标准命名规范。

| 序号 | 领域 | Tenant | 访问控制 |
| --- | --- | --- | --- |
| 1 | Fund Administration | Geneva | Requester AD Group / Approver AD group |
| 2 | Fund Administration | Icon | Requester AD Group / Approver AD group |
| 3 | Fund Administration | MF/MS | Requester AD Group / Approver AD group |
| 4 | Fund Administration | pControl | Requester AD Group / Approver AD group |
| 5 | Custody | Custody Unity | Requester AD Group / Approver AD group |
| 6 | Transfer Agency | GTAP | Requester AD Group / Approver AD group |
| 7 | Treasury | Treasury | Requester AD Group / Approver AD group |
| 8 | Middle office | HSS trade flow | Requester AD Group / Approver AD group |
| 9 | Middle office | Markit EDM | Requester AD Group / Approver AD group |
| 10 | Middle office | Calypso | Requester AD Group / Approver AD group |
| 10 | Securities lending | Globalone | Requester AD Group / Approver AD group |

## 4. Data Architecture chang / 数据架构变更

### 4.1 Data Model enhancement / 数据模型增强

### English

Require an approval table to hold data uploaded or changed by requestor. This record remains in approval table with an approval status either Approved or Rejected or Pending) and with remarks.

### 中文

需要一个 approval table 来保存由 requestor 上传或修改的数据。该记录保留在 approval table 中，并带有审批状态（Approved、Rejected 或 Pending）以及备注信息。

### 4.2 Attribute changes / 属性变更

### English

Enhance existing entities with the following additional attributes to be maintained in each entity

| Attr# | Field Name | Field Description | Data type / Values | Remarks |
| --- | --- | --- | --- | --- |
| 1 | Requester_ID | To capture the changes done by Requester (Maker) Employee number | Number (8 digit) | Auto populated by system |
| 2 | Approver_ID | To capture Approver(Checker) who validate and approve changes | Number (8 digit) | Auto populated by system |
| 3 | Requester_Timestamp | Date and timestamp that Requester (Maker) completes changes | Timestamp | Auto populated by system |
| 4 | Approver_Timestamp | Date and timestamp that Approver (Checker) approves changes | Timestamp | Auto populated by system |
| 5 | Version | Upon approval Version number will be generated for the change |  | Auto populated by system |
| 6 | Dictionary Action | Flag to Add or Update or Delete (Soft delete i.e. disable) of existing dictionary | A or U or D | Requester needs to update the action flag in UI or file |
| 7 | Approval Status | To indicate the approval status Approved or Pending or Rejected. By default, this will be populated as pending "P" | A or P or R | Auto populated based on approver action |
| 8 | Record Status | To indicate the record status in main table as Active or Disable upon approval by approver and based on Requester update in "Dictionary Action" attribute | A or D | Auto populated based on approver action |

### 中文

需要为现有实体增加以下属性，并在每个实体中维护这些新增字段。

| 属性序号 | 字段名 | 字段说明 | 数据类型 / 取值 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | Requester_ID | 用于记录 Requester（Maker）执行变更的员工编号 | 数字（8位） | 系统自动填充 |
| 2 | Approver_ID | 用于记录执行校验并批准变更的 Approver（Checker） | 数字（8位） | 系统自动填充 |
| 3 | Requester_Timestamp | Requester（Maker）完成变更时的日期时间戳 | Timestamp | 系统自动填充 |
| 4 | Approver_Timestamp | Approver（Checker）批准变更时的日期时间戳 | Timestamp | 系统自动填充 |
| 5 | Version | 在批准后，会为该变更生成版本号 |  | 系统自动填充 |
| 6 | Dictionary Action | 用于标识对现有字典执行新增、更新或删除（软删除，即 disable）的标志 | A 或 U 或 D | Requester 需要在 UI 或文件中更新该 action 标志 |
| 7 | Approval Status | 用于标识审批状态为 Approved、Pending 或 Rejected。默认填充为 pending，即 "P" | A 或 P 或 R | 根据 approver 的操作自动填充 |
| 8 | Record Status | 用于标识主表中的记录状态，在 approver 批准后，并结合 Requester 在 "Dictionary Action" 属性中的更新，将其置为 Active 或 Disable | A 或 D | 根据 approver 的操作自动填充 |

### 4.3 Attribute version history / 属性版本历史

### English

Additional attributes to be created in addition to version to manage the validity of the version record,

| Attr# | Field Name | Field Description | Data type / Values | Remarks |
| --- | --- | --- | --- | --- |
| 1 | Effective from | To capture the timestamp of the record effective for the version the record was created | Timestamp | Auto populated by system |
| 2 | Effective to | To capture the timestamp of the record closure or validity of the version upon new version created | Timestamp | Auto populated by system |

### 中文

除 Version 之外，还需要新增以下属性，用于管理版本记录的有效性。

| 属性序号 | 字段名 | 字段说明 | 数据类型 / 取值 | 备注 |
| --- | --- | --- | --- | --- |
| 1 | Effective from | 用于记录该版本记录创建时开始生效的时间戳 | Timestamp | 系统自动填充 |
| 2 | Effective to | 用于记录当新版本创建时，该版本记录关闭或失效的时间戳 | Timestamp | 系统自动填充 |

## 5. Web page (UI) Enhancements / Web 页面（UI）增强

### 5.1 Maker steps for Bulk upload / Maker 的批量上传步骤

#### 5.1.1 Download Template for Data dictionaries / 下载 Data Dictionary 模板

### English

Change data dictionary template under download option to include the additional attributes mentioned in "4.2. Attribute changes" section

### 中文

修改下载入口下的数据字典模板，使其包含“4.2 Attribute changes”章节中提到的新增属性。

##### 5.1.1.1 Add the "Dictionary action" attribute in the template / 在模板中增加 “Dictionary action” 属性

### English

Add the Dictionary action attribute in the templates for data sets and attributes are as follows,

### 中文

在数据集与属性的模板中增加 Dictionary action 属性，具体如下。

#### 5.1.2 Upload file and screen changes / 上传文件及界面变更

### English

Upload file and amend the screen change as follows

- When the "Upload File" button is selected, a file explorer window will prompt the user to select a file for upload to DDS. The upload functionality will verify that the individual initiating the upload is a member of the "Requester" group (the Requester AD (Active Directory) group) for the relevant tenant) associated with the data domain specified in the template. Upon successful upload, the Requester can view the file's contents in the approver dashboard.
- Change the label to "Upload Data Dictionary Template" and "Download Data Dictionary Template" as shown in the above diagram.
- After successful upload, maker and all users can view the upload records in approver dashboard.

### 中文

上传文件，并按如下方式调整界面：

- 当选择 “Upload File” 按钮时，系统会弹出文件选择窗口，提示用户选择要上传到 DDS 的文件。上传功能会校验发起上传的人员是否属于模板中所指定数据域对应 tenant 的 “Requester” 组（即 Requester AD（Active Directory）组）。上传成功后，Requester 可以在 approver dashboard 中查看文件内容。
- 按钮标签调整为 “Upload Data Dictionary Template” 和 “Download Data Dictionary Template”，如上图所示。
- 上传成功后，maker 和所有用户都可以在 approver dashboard 中查看上传记录。

### 5.2 Maker steps for Self Service Display (SSD) UI Data Set pages / Maker 在 Self Service Display（SSD）UI 数据集页面上的步骤

### English

Incorporate the new fields outlined in the "4.2. Attribute changes" section into the data set view for all tables and their respective attributes. This enhancement should be applied across the following areas: Custody, Fund Accounting (FA), Transfer Agency (TA), Treasury, Middle Office, and Securities Lending. Records can be edited, deleted and updated at row level.

Any record changes either addition or update or delete will copied from current table to Approval table upon submit by selecting submit button.

### 中文

将“4.2 Attribute changes”章节中列出的新字段纳入所有表及其对应属性的数据集视图中。该增强应应用于以下领域：Custody、Fund Accounting（FA）、Transfer Agency（TA）、Treasury、Middle Office 和 Securities Lending。记录可以在行级进行编辑、删除和更新。

任何记录变更，无论是新增、更新还是删除，在选择 submit 按钮提交后，都将从当前表复制到 Approval table。

##### 5.2.1.1 To modify the contents of the row / 修改行内容

### English

Select the edit icon to edit the records content, once edit button selected then the screen provides editable form for the specific row, refer the following sample for edit screen,

### 中文

选择 edit 图标以编辑记录内容。点击 edit 按钮后，界面会为该特定行提供可编辑表单，编辑界面示例如下。

##### 5.2.1.2 To add the records / 新增记录

### English

Select the "+" to add new rows, and a sample row is as follows,

### 中文

选择 “+” 以新增行，示例行如下。

##### 5.2.1.3 To delete the records / 删除记录

### English

Select the [delete] icon on the row to delete the record

### 中文

选择该行上的 [delete] 图标以删除记录。

##### 5.2.1.4 Submit changes / 提交变更

### English

Upon the Requester (maker) performing an update, add, or delete of any records, it is essential that they select the Submit button to forward the changes for review by the approver (checker). Upon submission, all modified records will be copied to a temporary table for approver review and processing.

Upon successful changes, Requester need to select "Submit" button to submit the changes and this will also prompt a comments window, enabling the Requester to provide any relevant remarks. These comments will accompany the submission and be made available to the checker during their review.

### 中文

当 Requester（maker）对任意记录执行更新、新增或删除后，必须选择 Submit 按钮，将这些变更提交给 approver（checker）进行审核。提交后，所有被修改的记录都会复制到一个临时表中，供 approver 审核和处理。

在完成变更后，Requester 需要选择 “Submit” 按钮提交这些变更，同时系统会弹出 comments 窗口，使 Requester 可以填写相关备注。这些备注会随提交通知一起保留，并在 checker 审核时可见。

### 5.3 Approver Dashboard / 审批人仪表板

### English

The Approver Dashboard is a newly designed user interface aimed at streamlining the process of browsing, viewing, and to take action on submitted requests. The dashboard will support two distinct types of access: Approver and Viewer.

- Approver Access:

Users with approver access are responsible for reviewing pending requests. They can validate the details and, based on their assessment, either approve (fully or partially) or reject the records.

- Viewer Access:

Viewer access enables users to view all submitted requests. By default, the dashboard displays pending records ("Pending" tab). Additionally, users can review the history of their own submitted requests under the "My Requests" tab.

The following screen provides a visual representation of the user interface.

### 中文

Approver Dashboard 是一个新设计的用户界面，旨在简化对已提交请求的浏览、查看以及处理操作。该 dashboard 将支持两种不同类型的访问权限：Approver 和 Viewer。

- Approver Access：

具有 approver 权限的用户负责审核待处理请求。他们可以校验详情，并根据评估结果，对记录进行批准（全部或部分）或拒绝。

- Viewer Access：

Viewer 权限允许用户查看所有已提交请求。默认情况下，dashboard 显示待处理记录（“Pending” tab）。此外，用户还可以在 “My Requests” tab 下查看自己所提交请求的历史记录。

下方界面展示了该用户界面的可视化示意。

## 6. Approver (Checker) steps for review and approve or reject changes / Approver（Checker）审核并批准或拒绝变更的步骤

### English

- Users are granted access to the Approver Dashboard, which allows them to view modifications made to records and track the ongoing approval status for each item. This functionality supports effective oversight and ensures transparency throughout the approval process.
- To review, approve, or reject a change, the approver must be a member of the designated Approver Active Directory (AD) group. Only individuals with this group membership are authorised to carry out approval actions on change requests.
- If the record was bulk uploaded or added or deleted by maker, then the following screen will be displayed for pending actions from checker in approver dashboard. Once a change has been approved or rejected, a pop-up window will appear, allowing the checker to enter their comments.
- If the record was updated by maker, then it displays new values and previous values will be appeared in approver Dashboard, as shown below, once approved or rejected the change, then a pop-up window will be appeared where checker can enter the comments.

Illustration of selecting multiple records for approval or rejection is shown below. After the action is taken, a pop-up window will appear, allowing the checker to enter their comments. This will be recorded in the system.

Users can view the records and its status whether it is approved, rejected or pending and relevant comments

### 中文

- 用户将获得 Approver Dashboard 的访问权限，从而可以查看对记录所做的修改，并跟踪每一项的持续审批状态。该功能支持有效监督，并确保整个审批过程的透明性。
- 若要审核、批准或拒绝一项变更，approver 必须是指定的 Approver Active Directory（AD）组成员。只有属于该组的人员才有权对变更请求执行审批操作。
- 如果该记录是由 maker 通过批量上传、新增或删除方式提交的，那么 approver dashboard 中将显示对应的 checker 待处理界面。一旦变更被批准或拒绝，系统会弹出一个窗口，允许 checker 输入评论。
- 如果该记录是由 maker 更新的，那么在 approver dashboard 中会显示新值与旧值，如下所示；一旦该变更被批准或拒绝，也会弹出一个窗口供 checker 输入评论。

下方展示了对多条记录执行批准或拒绝选择的示意图。在操作完成后，系统会弹出一个窗口，允许 checker 输入评论。这些评论会被记录在系统中。

用户可以查看记录及其状态，包括 approved、rejected 或 pending，以及相关评论。

## 7. Master Search Results (Nice to Have) / 主搜索结果（Nice to Have）

### English

- Provision search for new fields mentioned "2. Attribute changes" section, such as Maker, checker, Version, Date etc

### 中文

- 为“2. Attribute changes”章节中提到的新字段提供搜索能力，例如 Maker、checker、Version、Date 等。

## 8. Help content enhancements / Help 内容增强

### English

- update "Help" hyperlink text with approver (checker) and Requester (maker) process details as mentioned in section 2.

### 中文

- 更新 “Help” 超链接文本，加入第 2 节中提到的 approver（checker）与 Requester（maker）流程说明。

## 9. System Validations / 系统校验

### 9.1 Bulk upload file validations / 批量上传文件校验

### English

1. Check for file duplication
2. Requester (Maker) actions
   a. Maker will upload the file selecting the upload button
   b. Compare previous version and create an audit log for the changes in new version with audit timestamp for changes.
   c. Validate the files for errors and send or display errors and mention to correct errors before upload, some of the data validation logics for the file contents are mentioned in Data validations section
3. upon successful validation the file will be uploaded and success notification to be displayed or an email sent to the Checker

### 中文

1. 检查文件是否重复。
2. Requester（Maker）动作：
   a. Maker 通过选择上传按钮上传文件。
   b. 对比前一版本，并为新版本中的变更创建审计日志，同时记录审计时间戳。
   c. 对文件进行错误校验，并发送或展示错误信息，提示在上传前修正错误；部分文件内容的数据校验逻辑见 Data validations 章节。
3. 在校验成功后，文件将被上传，并显示成功通知，或向 Checker 发送邮件。

### 9.2 User Validations / 用户校验

### English

1. Ensure that Requester (maker) is a member of Requester AD group of the respective tenant
2. Ensure that Approver (checker) is from the Approver AD group of the respective tenant
3. Ensure Requester and Approver ID are not the same

### 中文

1. 确保 Requester（maker）属于对应 tenant 的 Requester AD group。
2. 确保 Approver（checker）来自对应 tenant 的 Approver AD group。
3. 确保 Requester 和 Approver 的 ID 不相同。

### 9.3 Data validations / 数据校验

### English

1. Check for duplicate records based on primary key or composite key
2. Check for not null for mandatory fields
3. Check for any special characters in the content
4. Check for the list of values in the range
5. Check for the data types, length etc

### 中文

1. 基于主键或组合键检查重复记录。
2. 检查必填字段是否非空。
3. 检查内容中是否包含特殊字符。
4. 检查取值列表是否在允许范围内。
5. 检查数据类型、长度等。

### 9.4 Approver (Checker) Validations / Approver（Checker）校验

### English

Approver will validate the file

a. Approver will validate the records by either approving or rejecting the change.
b. To approve the records, checker will select the records and select approve option and submit.
c. Approver can reject the file by selecting reject button option, which pops up a window where approver will enter the reject reason and submit.
d. Upon reject submission the records in Approval table's approval status changed to rejected.
e. Upon successful approval of changes then one of the following 3 actions will be performed

- If the Data dictionary action value is "U" then the existing record will be updated with the new records with new version number
- If the Data dictionary action value is "D" then the existing record will be updated the record status as "D" to disable or soft deletion of record
- If the Data dictionary action value is "A" then record will be added to the existing or new tables.
- All the changes on data dictionary services will create an audit log with details inclusive of tenant name, checker name, maker name, Date of change etc with previous value and new value.

f. Upon successful approver process completed, based dictionary action flag the following action will be performed

i. If Addition or update feature got approved, then the new version will be tagged and released.
ii. If dictionary action is "D" then the record will be disabled by updating the record status to "D".

### 中文

Approver 将对文件进行校验。

a. Approver 通过批准或拒绝变更的方式对记录进行校验。  
b. 若要批准记录，checker 会先选择记录，再选择 approve 选项并提交。  
c. Approver 可以通过选择 reject 按钮拒绝该文件，系统会弹出窗口，要求 approver 输入拒绝原因并提交。  
d. 在提交拒绝后，Approval table 中这些记录的 approval status 会变为 rejected。  
e. 当变更成功获批后，将执行以下 3 种动作之一：

- 如果 Data dictionary action 的值为 “U”，则现有记录会用新记录进行更新，并生成新的版本号。
- 如果 Data dictionary action 的值为 “D”，则现有记录的 record status 会更新为 “D”，表示禁用或软删除该记录。
- 如果 Data dictionary action 的值为 “A”，则记录会被添加到现有表或新表中。
- Data dictionary services 上发生的所有变更都会创建审计日志，其中包括 tenant name、checker name、maker name、Date of change 等信息，以及旧值和新值。

f. 在 approver 流程成功完成后，系统会基于 dictionary action 标志执行以下动作：

i. 如果新增或更新功能获得批准，则新版本会被打标签并发布。  
ii. 如果 dictionary action 为 “D”，则会通过将 record status 更新为 “D” 来禁用该记录。

## 10. Versioning and History records management / 版本与历史记录管理

### English

- Upon successful validation and approved by approver, a version number will be assigned to each record. For new records, the version will begin at 1.0. For updates, the version number will increment by one (e.g., if the current version is 1.0, the next will be 2.0). nice to have if we have dates
- When a record is updated, the "effective to" attribute of the previous version must be set to the current timestamp, indicating the closure of that version.
- The new version will be created with the "effective from" attribute set to the current timestamp.
- It is essential to ensure that there is no overlap between the "effective to" timestamp of the previous version and the "effective from" timestamp of the new version.
- Version numbers must always increase sequentially and cannot be reused or skipped.
- Enhance system performance, historical records and previous versions may be partitioned or maintained in dedicated tables. The solution team will recommend an approach for managing these history records, including how access and visibility will be provided to designated users, such as Requesters and Approvers.

### 中文

- 在成功校验并获得 approver 批准后，每条记录都会被分配一个版本号。对于新记录，版本从 1.0 开始；对于更新，版本号按 1 递增（例如当前版本为 1.0，则下一个版本为 2.0）。如果带日期信息则更好（nice to have）。
- 当记录被更新时，前一个版本的 “effective to” 属性必须设置为当前时间戳，以表示该版本结束。
- 新版本将以当前时间戳作为 “effective from” 属性创建。
- 必须确保前一个版本的 “effective to” 时间戳与新版本的 “effective from” 时间戳之间不存在重叠。
- 版本号必须始终按顺序递增，不能重复使用，也不能跳号。
- 为提升系统性能，历史记录和旧版本可以按分区方式管理，或保存在专用表中。解决方案团队将建议一种管理这些历史记录的方法，包括如何为指定用户（例如 Requester 和 Approver）提供访问与可见性。

## 11. Audit Capture / 审计捕获

### English

Upon successful approval, Approval table contents will be updated to main table and an audit log created with details of tenant name, checker name, maker name, Date of change, Action type, previous value and new value.

### 中文

在审批成功后，Approval table 中的内容将更新到主表，同时会创建审计日志，记录 tenant name、checker name、maker name、Date of change、Action type、previous value 和 new value 等详细信息。
