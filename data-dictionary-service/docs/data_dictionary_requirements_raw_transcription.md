# Data Dictionary Requirement Specifications - Raw Transcription

## 1. Enhancements for Maker (Requester) and Checker (Approver) process

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

## 2. User Journey for bulk upload and edit record using UI

### 2.1 Bulk upload

1. Identify the need for a new or updated data dictionary entry. Download the relevant template for data dictionary submission.
2. Preparation of file for upload and review to ensure accuracy and completeness.
3. Submission: Upload the completed entry to the Data Dictionary (DD) services.
4. Approver (Checker) Review: The checker reviews the submitted entry for quality, compliance, and alignment with standards.
5. Feedback or Approval:
   a. If issues are found, the checker rejects the change and notifies the maker for revision, efficient notification mechanism to be adapted.
   b. If approved, the checker versions the data dictionary entry.
6. Release: The approved data dictionary version is released to users.
7. Completion: The process concludes.

### 2.2 Update/Delete/Add using UI

1. Update/ Add/ Delete of records in data mesh
2. Submit changes
3. Approver (Checker) Review: The checker reviews the submitted entry for quality, compliance, and alignment with standards.
4. Feedback or Approval:
   a. If issues are found, the checker rejects the change and notifies the maker for revision.
   b. If approved, approved record will be created as new version and if old record exists then it will be closed.
5. Release: The approved data dictionary version is released to users.
6. Completion: The process concludes.

## 3. Access Management using AD groups

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

## 4. Data Architecture chang

### 4.1 Data Model enhancement

Require an approval table to hold data uploaded or changed by requestor. This record remains in approval table with an approval status either Approved or Rejected or Pending) and with remarks.

### 4.2 Attribute changes

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

### 4.3 Attribute version history

Additional attributes to be created in addition to version to manage the validity of the version record,

| Attr# | Field Name | Field Description | Data type / Values | Remarks |
| --- | --- | --- | --- | --- |
| 1 | Effective from | To capture the timestamp of the record effective for the version the record was created | Timestamp | Auto populated by system |
| 2 | Effective to | To capture the timestamp of the record closure or validity of the version upon new version created | Timestamp | Auto populated by system |

## 5. Web page (UI) Enhancements

### 5.1 Maker steps for Bulk upload

#### 5.1.1 Download Template for Data dictionaries

Change data dictionary template under download option to include the additional attributes mentioned in "4.2. Attribute changes" section

##### 5.1.1.1 Add the "Dictionary action" attribute in the template

Add the Dictionary action attribute in the templates for data sets and attributes are as follows,

#### 5.1.2 Upload file and screen changes

Upload file and amend the screen change as follows

- When the "Upload File" button is selected, a file explorer window will prompt the user to select a file for upload to DDS. The upload functionality will verify that the individual initiating the upload is a member of the "Requester" group (the Requester AD (Active Directory) group) for the relevant tenant) associated with the data domain specified in the template. Upon successful upload, the Requester can view the file's contents in the approver dashboard.
- Change the label to "Upload Data Dictionary Template" and "Download Data Dictionary Template" as shown in the above diagram.
- After successful upload, maker and all users can view the upload records in approver dashboard.

### 5.2 Maker steps for Self Service Display (SSD) UI Data Set pages

Incorporate the new fields outlined in the "4.2. Attribute changes" section into the data set view for all tables and their respective attributes. This enhancement should be applied across the following areas: Custody, Fund Accounting (FA), Transfer Agency (TA), Treasury, Middle Office, and Securities Lending. Records can be edited, deleted and updated at row level.

Any record changes either addition or update or delete will copied from current table to Approval table upon submit by selecting submit button.

##### 5.2.1.1 To modify the contents of the row

Select the edit icon to edit the records content, once edit button selected then the screen provides editable form for the specific row, refer the following sample for edit screen,

##### 5.2.1.2 To add the records

Select the "+" to add new rows, and a sample row is as follows,

##### 5.2.1.3 To delete the records

Select the [delete] icon on the row to delete the record

##### 5.2.1.4 Submit changes

Upon the Requester (maker) performing an update, add, or delete of any records, it is essential that they select the Submit button to forward the changes for review by the approver (checker). Upon submission, all modified records will be copied to a temporary table for approver review and processing.

Upon successful changes, Requester need to select "Submit" button to submit the changes and this will also prompt a comments window, enabling the Requester to provide any relevant remarks. These comments will accompany the submission and be made available to the checker during their review.

### 5.3 Approver Dashboard

The Approver Dashboard is a newly designed user interface aimed at streamlining the process of browsing, viewing, and to take action on submitted requests. The dashboard will support two distinct types of access: Approver and Viewer.

- Approver Access:

Users with approver access are responsible for reviewing pending requests. They can validate the details and, based on their assessment, either approve (fully or partially) or reject the records.

- Viewer Access:

Viewer access enables users to view all submitted requests. By default, the dashboard displays pending records ("Pending" tab). Additionally, users can review the history of their own submitted requests under the "My Requests" tab.

The following screen provides a visual representation of the user interface.

## 6. Approver (Checker) steps for review and approve or reject changes

- Users are granted access to the Approver Dashboard, which allows them to view modifications made to records and track the ongoing approval status for each item. This functionality supports effective oversight and ensures transparency throughout the approval process.
- To review, approve, or reject a change, the approver must be a member of the designated Approver Active Directory (AD) group. Only individuals with this group membership are authorised to carry out approval actions on change requests.
- If the record was bulk uploaded or added or deleted by maker, then the following screen will be displayed for pending actions from checker in approver dashboard. Once a change has been approved or rejected, a pop-up window will appear, allowing the checker to enter their comments.
- If the record was updated by maker, then it displays new values and previous values will be appeared in approver Dashboard, as shown below, once approved or rejected the change, then a pop-up window will be appeared where checker can enter the comments.

Illustration of selecting multiple records for approval or rejection is shown below. After the action is taken, a pop-up window will appear, allowing the checker to enter their comments. This will be recorded in the system.

Users can view the records and its status whether it is approved, rejected or pending and relevant comments

## 7. Master Search Results (Nice to Have)

- Provision search for new fields mentioned "2. Attribute changes" section, such as Maker, checker, Version, Date etc

## 8. Help content enhancements

- update "Help" hyperlink text with approver (checker) and Requester (maker) process details as mentioned in section 2.

## 9. System Validations

### 9.1 Bulk upload file validations

1. Check for file duplication
2. Requester (Maker) actions
   a. Maker will upload the file selecting the upload button
   b. Compare previous version and create an audit log for the changes in new version with audit timestamp for changes.
   c. Validate the files for errors and send or display errors and mention to correct errors before upload, some of the data validation logics for the file contents are mentioned in Data validations section
3. upon successful validation the file will be uploaded and success notification to be displayed or an email sent to the Checker

### 9.2 User Validations

1. Ensure that Requester (maker) is a member of Requester AD group of the respective tenant
2. Ensure that Approver (checker) is from the Approver AD group of the respective tenant
3. Ensure Requester and Approver ID are not the same

### 9.3 Data validations

1. Check for duplicate records based on primary key or composite key
2. Check for not null for mandatory fields
3. Check for any special characters in the content
4. Check for the list of values in the range
5. Check for the data types, length etc

### 9.4 Approver (Checker) Validations

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

## 10. Versioning and History records management

- Upon successful validation and approved by approver, a version number will be assigned to each record. For new records, the version will begin at 1.0. For updates, the version number will increment by one (e.g., if the current version is 1.0, the next will be 2.0). nice to have if we have dates
- When a record is updated, the "effective to" attribute of the previous version must be set to the current timestamp, indicating the closure of that version.
- The new version will be created with the "effective from" attribute set to the current timestamp.
- It is essential to ensure that there is no overlap between the "effective to" timestamp of the previous version and the "effective from" timestamp of the new version.
- Version numbers must always increase sequentially and cannot be reused or skipped.
- Enhance system performance, historical records and previous versions may be partitioned or maintained in dedicated tables. The solution team will recommend an approach for managing these history records, including how access and visibility will be provided to designated users, such as Requesters and Approvers.

## 11. Audit Capture

Upon successful approval, Approval table contents will be updated to main table and an audit log created with details of tenant name, checker name, maker name, Date of change, Action type, previous value and new value.
