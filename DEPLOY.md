# SaveIt — One-time Azure deployment guide

This walks through the **manual one-time setup** required before the GitHub
Actions pipeline (`.github/workflows/deploy.yml`) can roll out new versions
automatically. Everything in this file is run interactively from your laptop
once. After it's done, every push to `main` deploys.

> Phase 6 sets up the platform with **no auth yet** — the Container App will be
> publicly reachable. Add Entra External Identities (Phase 7) before announcing
> the URL anywhere.

---

## 0. Prerequisites

```bash
brew install azure-cli docker
az login
az account set --subscription "<your-subscription-id>"
```

Set a few shell variables you'll reuse:

```bash
export RG=saveit-rg
export LOCATION=westus3        # or eastus2
export APP_NAME=saveit
export GH_REPO=<your-gh-user>/finapp     # owner/repo
```

---

## 1. Create the resource group

```bash
az group create -n "$RG" -l "$LOCATION"
```

---

## 2. Deploy infrastructure (Bicep)

Pick a strong Postgres password (16+ chars, mix of classes — Postgres Flex
rejects weak passwords):

```bash
export PG_PASS='<paste a strong password here>'

az deployment group create \
  -g "$RG" \
  -f infra/main.bicep \
  -p infra/main.parameters.json \
  -p pgAdminPassword="$PG_PASS"
```

Capture outputs:

```bash
export ACR_NAME=$(az deployment group show -g "$RG" -n main --query properties.outputs.acrName.value -o tsv)
export ACA_NAME=$(az deployment group show -g "$RG" -n main --query properties.outputs.acaName.value -o tsv)
export ACA_FQDN=$(az deployment group show -g "$RG" -n main --query properties.outputs.acaFqdn.value -o tsv)
export KV_NAME=$(az deployment group show -g "$RG" -n main --query properties.outputs.keyVaultName.value -o tsv)
export MI_PRINCIPAL=$(az deployment group show -g "$RG" -n main --query properties.outputs.managedIdentityPrincipalId.value -o tsv)

echo "ACR=$ACR_NAME  ACA=$ACA_NAME  FQDN=$ACA_FQDN"
```

---

## 3. First image push (so ACA has something real to run)

The Bicep file deploys a placeholder quickstart image. Replace it with a real
build of SaveIt.

> **Apple Silicon / ARM users:** ACA only runs `linux/amd64`. A plain
> `docker build` on an M1/M2/M3 Mac produces an arm64 image that ACA will
> reject with `no child with platform linux/amd64 in index ...`. Use
> `docker buildx --platform linux/amd64` instead (shown below).

```bash
az acr login --name "$ACR_NAME"

# Cross-platform build (works on Intel Macs and Linux too)
docker buildx create --use --name saveit-builder 2>/dev/null || docker buildx use saveit-builder
docker buildx build \
  --platform linux/amd64 \
  -t "$ACR_NAME.azurecr.io/saveit:bootstrap" \
  --push \
  .

az containerapp update \
  --name "$ACA_NAME" --resource-group "$RG" \
  --image "$ACR_NAME.azurecr.io/saveit:bootstrap"
```

Verify:

```bash
curl -fsS "https://$ACA_FQDN/api/health"
# {"ok":true,"env":"prod"}
```

---

## 4. Set up GitHub Actions OIDC (no secrets in GitHub)

Create an Entra app registration that GitHub Actions will impersonate via OIDC:

```bash
APP_ID=$(az ad app create --display-name "saveit-gha" --query appId -o tsv)
az ad sp create --id "$APP_ID"
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)
SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Federated credential for pushes to main
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "gha-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:'"$GH_REPO"':ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# Federated credential for the production environment (matches deploy.yml)
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "gha-env-prod",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:'"$GH_REPO"':environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}'

# Grant the SP just enough on the resource group
az role assignment create --assignee "$SP_OBJECT_ID" \
    --role "Contributor" \
    --scope "/subscriptions/$SUB_ID/resourceGroups/$RG"
az role assignment create --assignee "$SP_OBJECT_ID" \
    --role "AcrPush" \
    --scope "$(az acr show -n "$ACR_NAME" --query id -o tsv)"
```

Add to your GitHub repo:

**Repository variables** (Settings → Secrets and variables → Actions → Variables):

| Name      | Value          |
|-----------|----------------|
| AZURE_RG  | $RG            |
| ACR_NAME  | $ACR_NAME      |
| ACA_NAME  | $ACA_NAME      |

**Repository secrets** (Settings → Secrets and variables → Actions → Secrets):

| Name                  | Value         |
|-----------------------|---------------|
| AZURE_CLIENT_ID       | $APP_ID       |
| AZURE_TENANT_ID       | $TENANT_ID    |
| AZURE_SUBSCRIPTION_ID | $SUB_ID       |

Then create a `production` GitHub Environment (Settings → Environments → New
environment → `production`). The workflow gates the deploy job behind it so
you can add manual approvers later if you want.

---

## 5. Push to main

```bash
git push origin main
```

The `deploy` workflow runs `pytest`, builds the multi-stage Dockerfile, pushes
the image to ACR, and rolls out the new revision. Watch it in the **Actions**
tab.

---

## 6. (Optional) Custom domain

Once you have a domain (e.g. `saveit.app`):

```bash
az containerapp hostname add \
  -n "$ACA_NAME" -g "$RG" --hostname app.saveit.app
az containerapp ssl bind \
  -n "$ACA_NAME" -g "$RG" --hostname app.saveit.app --environment "$APP_NAME-env"
```

Add the CNAME record your registrar requires (the `add` command prints it).
Then set repository variable `CORS_ORIGINS=https://app.saveit.app` and update
the Container App env var.

---

## 7. What's deferred to later phases

| Phase | What it adds                                                          |
|-------|-----------------------------------------------------------------------|
| 7     | Microsoft Entra External Identities — open sign-up + per-user data    |
| 8     | Move PDFs from local FS to Blob Storage (`users/{user_id}/{sha}.pdf`) |
| 9     | Move Azure DI key into Key Vault (replaces per-user Settings UI)      |
| 10    | Per-user anti-abuse rate limits + admin dashboard                     |
| 11+   | Budgets, debit accounts, AI assistant, observability, legal pages     |

---

## Troubleshooting

**Container app keeps restarting**
- `az containerapp logs show -n "$ACA_NAME" -g "$RG" --tail 200 --follow`
- Most common cause: `alembic upgrade head` failing because the Postgres
  firewall doesn't allow Azure services. Re-run the Bicep deploy.

**Image pull fails**
- The user-assigned MI needs `AcrPull` on the registry. The Bicep template
  assigns it; if you renamed things, add it manually:
  `az role assignment create --assignee <MI client id> --role AcrPull --scope <ACR resource id>`

**Postgres connection rejected**
- The Bicep `AllowAzureServices` rule (`0.0.0.0`–`0.0.0.0`) is what permits
  ACA to reach Postgres. Don't remove it until you switch to a private
  endpoint in Phase 14 hardening.

**`VaultAlreadyExists` after re-deploying to a new RG with the same name**
- Key Vault uses soft-delete with a 7-day retention, so deleting the RG only
  tombstones the vault — its name is reserved.
- `uniqueString(resourceGroup().id)` is deterministic per (subscription, RG
  name), so a new RG with the same name produces the same vault name and
  collides with the tombstone.
- Fix:
  ```
  az keyvault list-deleted --query "[?name=='<vault-name>']" -o table
  az keyvault purge --name <vault-name>
  # then re-run `az deployment group create ...`
  ```
- To avoid it altogether on full retries, give the RG a fresh name (e.g.
  `SaveIt-RG-2`) so the unique suffix changes.

**`LocationIsOfferRestricted` on Postgres Flexible Server**
- New pay-as-you-go subscriptions are quota-blocked from some regions
  (commonly `eastus`). Postgres Flex is the resource that fails first.
- Tear down the RG and recreate it in a different region:
  ```
  az group delete -n "$RG" --yes --no-wait
  az group create  -n "$RG" -l westus3        # try westus3, westus2, centralus, mexicocentral
  ```
  Then re-run the Bicep deploy. The template uses `resourceGroup().location`,
  so changing the RG region is enough — no parameter changes needed.
- Permanent fix (slower): request quota exception at
  https://aka.ms/postgres-request-quota-increase
