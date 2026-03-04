# Deployment Runbook Template (GCP + Ansible)

Use this template for deploying `coordinator-service` to GCP Cloud Run.

---

## 1. Document Metadata

- Service: `coordinator-service`
- Environment: `<dev|sit|uat|prod>`
- Region: `<region>`
- Owner: `<team_or_owner>`
- Last updated: `<YYYY-MM-DD>`
- Change ticket: `<ticket_id>`

---

## 2. Deployment Scope

This deployment covers:

1. Build and push container image
2. Run DB migrations (Cloud Run Job + Alembic)
3. Deploy Cloud Run Service via Ansible
4. Smoke test and rollback readiness

---

## 3. Pre-Deployment Preparation

## 3.1 Enable Required GCP APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  vpcaccess.googleapis.com
```

## 3.2 Create Service Accounts

Recommended split:

- Runtime SA: used by Cloud Run service/job
- Deployer SA: used by CI/CD or operator to run Ansible/gcloud

```bash
gcloud iam service-accounts create coordinator-runtime \
  --display-name="Coordinator Runtime SA"

gcloud iam service-accounts create coordinator-deployer \
  --display-name="Coordinator Deployer SA"
```

## 3.3 Assign IAM Roles

### Runtime SA (minimum baseline)

- `roles/cloudsql.client`
- `roles/cloudsql.instanceUser` (for IAM DB auth)
- `roles/secretmanager.secretAccessor`
- `roles/logging.logWriter` (usually inherited, set explicitly if required)

```bash
gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:coordinator-runtime@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:coordinator-runtime@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/cloudsql.instanceUser"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:coordinator-runtime@<PROJECT_ID>.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Deployer SA (example)

- `roles/run.admin`
- `roles/iam.serviceAccountUser`
- `roles/cloudbuild.builds.editor`
- `roles/artifactregistry.writer`
- `roles/cloudsql.admin` (if managing SQL infra)
- `roles/secretmanager.admin` (if managing secrets)

Adjust to least privilege for your organization policy.

## 3.4 Create Cloud SQL (PostgreSQL)

1. Create instance and database
2. Enable IAM DB auth
3. Create IAM DB user matching `DB_IAM_USER`

Example:

```bash
gcloud sql instances create <INSTANCE_NAME> \
  --database-version=POSTGRES_14 \
  --region=<REGION>

gcloud sql databases create <DB_NAME> --instance=<INSTANCE_NAME>
```

Record:

- `INSTANCE_CONNECTION_NAME=<PROJECT_ID>:<REGION>:<INSTANCE_NAME>`
- `DB_NAME=<DB_NAME>`
- `DB_IAM_USER=<iam_user_email>`

## 3.5 Create Secrets (Secret Manager)

Create all runtime secrets before deployment.

Minimum examples:

- SMB password secret (name referenced by `SMB_SECRET_MANAGER_NAME`)
- JWT secret (`JWT_SECRET_FILE` or env-driven strategy)
- ITM OAuth credential secret
- IQube PKCS#12 + password (`IQUBE_P12`, `IQUBE_P12_PASSWORD`) if mTLS is enabled

Example:

```bash
printf '%s' '<SMB_PASSWORD>' | gcloud secrets create smb-secret --data-file=-
```

If secret already exists:

```bash
printf '%s' '<NEW_VALUE>' | gcloud secrets versions add smb-secret --data-file=-
```

## 3.6 Network and SMB Connectivity

If SMB path is private/on-prem, prepare:

- Serverless VPC Access connector
- Route/firewall/VPN/interconnect
- DNS resolution for SMB host

Validate from runtime network path before go-live.

## 3.7 Artifact Registry

```bash
gcloud artifacts repositories create <REPO> \
  --repository-format=docker \
  --location=<REGION>
```

---

## 4. Build Image

Use immutable tag (commit SHA / release tag).

```bash
gcloud builds submit \
  --tag <REGION>-docker.pkg.dev/<PROJECT_ID>/<REPO>/coordinator-service:<IMAGE_TAG>
```

Image example:

`<REGION>-docker.pkg.dev/<PROJECT_ID>/<REPO>/coordinator-service:<IMAGE_TAG>`

---

## 5. Database Migration (Cloud Run Job)

This project uses Alembic. Run migrations before or together with service rollout.

Create/update migration job:

```bash
gcloud run jobs create coordinator-migrate \
  --image=<IMAGE_URI> \
  --region=<REGION> \
  --service-account=coordinator-runtime@<PROJECT_ID>.iam.gserviceaccount.com \
  --command=alembic \
  --args=upgrade \
  --args=head \
  --set-env-vars=ENV=<ENV>,PROJECT_ID=<PROJECT_ID>,INSTANCE_CONNECTION_NAME=<INSTANCE_CONNECTION_NAME>,DB_IAM_USER=<DB_IAM_USER>,DB_NAME=<DB_NAME>
```

Execute:

```bash
gcloud run jobs execute coordinator-migrate --region=<REGION> --wait
```

Expected result: migration execution succeeds with no schema errors.

---

## 6. Ansible Deployment

## 6.1 Example Variables (`group_vars/<env>.yml`)

```yaml
project_id: "<PROJECT_ID>"
region: "<REGION>"
service_name: "coordinator-service"
image_uri: "<REGION>-docker.pkg.dev/<PROJECT_ID>/<REPO>/coordinator-service:<IMAGE_TAG>"
runtime_service_account: "coordinator-runtime@<PROJECT_ID>.iam.gserviceaccount.com"

env_vars:
  ENV: "<ENV>"
  PROJECT_ID: "<PROJECT_ID>"
  INSTANCE_CONNECTION_NAME: "<INSTANCE_CONNECTION_NAME>"
  DB_IAM_USER: "<DB_IAM_USER>"
  DB_NAME: "<DB_NAME>"
  SMB_UNC_PATH: "<SMB_UNC_PATH>"
  SMB_ARCHIVE_SUBPATH: "<SMB_ARCHIVE_SUBPATH>"
  SMB_USERNAME: "<SMB_USERNAME>"
  SMB_SECRET_MANAGER_NAME: "smb-secret"
  FOI_API_URL: "<FOI_API_URL>"
  ITM_API_URL: "<ITM_API_URL>"
  IQUBE_API_URL: "<IQUBE_API_URL>"
  UI_DIST_DIR: "<OPTIONAL_UI_DIST_PATH>"

secrets_env:
  # key: secret_name
  smb-secret: "smb-secret:latest"
  iqube-p12: "iqube-p12:latest"
  iqube-p12-password: "iqube-p12-password:latest"
```

## 6.2 Run Playbook

```bash
ansible-playbook -i inventories/<env>/hosts deploy_cloud_run.yml \
  -e "target_env=<env>" \
  -e "image_tag=<IMAGE_TAG>"
```

Recommended playbook order:

1. Validate required vars/secrets
2. Deploy/Update Cloud Run Job (migration)
3. Execute migration job and wait
4. Deploy Cloud Run service
5. Run smoke checks

---

## 7. Post-Deployment Validation

## 7.1 Health/API Checks

```bash
curl -f https://<SERVICE_URL>/api/v1/healthz
```

## 7.2 Functional Smoke

- Trigger one run:
  - `POST /api/v1/coordinator/runs`
- Verify:
  - No fatal errors in response
  - Expected DB records written
  - Archive task scheduled/completed

## 7.3 Logging and Alerting Checks

- Confirm structured logs appear in Cloud Logging
- Validate key fields:
  - `event_code`, `client`, `status`, `alertable`, `retryable`
- Confirm alert policies are active

Reference: `docs/logging_alerting.md`

---

## 8. Rollback Plan

Rollback options:

1. Roll back Cloud Run traffic to previous revision
2. Re-deploy previous known-good image tag via Ansible
3. If migration introduced incompatible changes, follow DB rollback plan for that release

Rollback command example (if needed):

```bash
gcloud run services update-traffic coordinator-service \
  --region=<REGION> \
  --to-revisions=<PREVIOUS_REVISION>=100
```

---

## 9. Change Record

- Image tag deployed: `<IMAGE_TAG>`
- Cloud Run revision: `<REVISION_NAME>`
- Migration revision: `<ALEMBIC_HEAD>`
- Operator: `<NAME>`
- Date/time: `<UTC_TIMESTAMP>`
- Result: `<SUCCESS|FAILED>`

---

## 10. Quick Checklist

- [ ] APIs enabled
- [ ] Runtime SA / Deployer SA created
- [ ] IAM roles assigned
- [ ] Cloud SQL ready + IAM DB user ready
- [ ] Secrets created and accessible
- [ ] Network path to SMB validated
- [ ] Image built and pushed
- [ ] Alembic migration job executed successfully
- [ ] Cloud Run service deployed via Ansible
- [ ] Health + functional smoke passed
- [ ] Logging/alerts verified
