// SaveIt — Azure infrastructure (multi-tenant SaaS)
// Deploys: ACR + Postgres Flexible Server + Storage + Log Analytics + App Insights
//          + User-assigned Managed Identity + Key Vault
//          + Container Apps Environment + Container App
//
// Out-of-scope here (manual one-time steps, see DEPLOY.md):
//   - Microsoft Entra External Identities tenant + app registrations (Phase 7)
//   - Azure Document Intelligence resource (region availability varies)
//   - Azure OpenAI resource (regional approval required)

@description('Short name used as a prefix for every resource (3-12 chars, lowercase).')
@minLength(3)
@maxLength(12)
param appName string = 'saveit'

@description('Deployment region. westus3 and eastus2 both have Postgres Flex + ACA + AOAI.')
param location string = resourceGroup().location

@description('Postgres administrator login.')
param pgAdmin string = 'saveitadmin'

@secure()
@description('Postgres administrator password (also stored as a Key Vault secret).')
param pgAdminPassword string

@description('Container image to deploy. After first deploy, GitHub Actions overrides this.')
param containerImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Comma-separated list of CORS origins for the API.')
param corsOrigins string = 'https://${appName}.example.com'

var suffix = uniqueString(resourceGroup().id)
var acrName = toLower('${appName}acr${suffix}')
var kvName = toLower('${appName}-kv-${substring(suffix, 0, 6)}')
var pgName = toLower('${appName}-pg-${substring(suffix, 0, 6)}')
var stgName = toLower('${appName}st${substring(suffix, 0, 8)}')
var lawName = '${appName}-law'
var aiName = '${appName}-ai'
var miName = '${appName}-mi'
var acaEnvName = '${appName}-env'
var acaAppName = appName

resource mi 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: miName
  location: location
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }
}

resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, mi.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
    IngestionMode: 'LogAnalytics'
  }
}

resource stg 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: stgName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: stg
  name: 'default'
}

resource pdfsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'pdfs'
  properties: { publicAccess: 'None' }
}

resource blobContribRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(stg.id, mi.id, 'BlobDataContributor')
  scope: stg
  properties: {
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { name: 'standard', family: 'A' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource kvSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, mi.id, 'KeyVaultSecretsUser')
  scope: kv
  properties: {
    principalId: mi.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
  }
}

resource pgPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'pg-password'
  properties: { value: pgAdminPassword }
}

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: pgName
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: pgAdmin
    administratorLoginPassword: pgAdminPassword
    storage: { storageSizeGB: 32, autoGrow: 'Enabled' }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

resource pgFwAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: pg
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource pgDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: pg
  name: 'saveit'
  properties: { charset: 'UTF8', collation: 'en_US.utf8' }
}

resource acaEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: acaEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

resource aca 'Microsoft.App/containerApps@2024-03-01' = {
  name: acaAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${mi.id}': {} }
  }
  properties: {
    environmentId: acaEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: '${acrName}.azurecr.io'
          identity: mi.id
        }
      ]
      secrets: [
        {
          name: 'database-url'
          value: 'postgresql+psycopg://${pgAdmin}:${pgAdminPassword}@${pg.properties.fullyQualifiedDomainName}:5432/saveit?sslmode=require'
        }
        {
          name: 'appinsights-conn'
          value: appInsights.properties.ConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'app'
          image: containerImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'ENV', value: 'prod' }
            { name: 'SERVE_FRONTEND', value: 'true' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'AZURE_STORAGE_ACCOUNT', value: stg.name }
            { name: 'AZURE_STORAGE_CONTAINER', value: 'pdfs' }
            { name: 'AZURE_KEY_VAULT_URL', value: kv.properties.vaultUri }
            { name: 'CORS_ORIGINS', value: corsOrigins }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'appinsights-conn' }
            { name: 'AZURE_CLIENT_ID', value: mi.properties.clientId }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 20
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
  dependsOn: [
    acrPullRole
    blobContribRole
    kvSecretsUser
    pgFwAzure
    pgDb
  ]
}

output acrLoginServer string = '${acrName}.azurecr.io'
output acrName string = acrName
output acaName string = aca.name
output acaFqdn string = aca.properties.configuration.ingress.fqdn
output keyVaultName string = kvName
output managedIdentityClientId string = mi.properties.clientId
output managedIdentityPrincipalId string = mi.properties.principalId
output postgresHost string = pg.properties.fullyQualifiedDomainName
output storageAccount string = stg.name
