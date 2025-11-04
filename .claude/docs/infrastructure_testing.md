# Local Testing and PGBouncer Information

## Running TestKube Tests Locally

### Prerequisites

1. **Kubernetes Context**: Switch to the correct context
   ```bash
   kubectl config use-context fbg-inf-dev-1
   # Alias: kcuc fbg-inf-dev-1
   ```

2. **TestKube CLI**: Install TestKube CLI following [TestKube documentation](https://docs.testkube.io/getting-started/step1-installing-cli)

3. **Secrets**: Tests use the `performance-cicd-credentials` secret in the `testkube` namespace which contains:
   - NATS credentials (nats-username, nats-password)
   - IGT credentials (igt-user, igt-password)
   - Various API client secrets and keys

### Running Tests

**CRITICAL**: Always explicitly specify the Kubernetes context to prevent accidental deployments to wrong environments.

#### TestKube CLI Setup and Execution

```bash
# 1. Set current kubectl context first (for safety)
kubectl config use-context fbg-inf-dev-1

# 2. Configure testkube to use proxy client mode with current context
testkube set context --client proxy --kubeconfig ~/.kube/config --namespace testkube

# 3. Run TestWorkflows with watch for real-time output
testkube run testworkflow k6-pgbouncer-rolling-restart-psql --watch

# Alternative method if testkube CLI has connection issues:
kubectl create -f - <<EOF
apiVersion: testworkflows.testkube.io/v1
kind: TestWorkflowExecution
metadata:
  name: pgbouncer-test-\$(date +%s)
  namespace: testkube
spec:
  testWorkflow:
    name: k6-pgbouncer-rolling-restart-psql
EOF
```

#### Legacy Test Commands (for older Test CRDs)

```bash
# Basic test execution - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 testkube run test <test-name> -v TEST_ENVIRONMENT=fbg-inf-dev-1

# With secret variables - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 testkube run testworkflow casino-bet-placement-v2 \
  -v TEST_ENVIRONMENT=fbg-inf-dev-1 \
  --secret-variable IGT_USER=username \
  --secret-variable IGT_PW=password

# Deployment - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 apply -f tests/your-service/your-test.yaml

# General kubectl commands - ALWAYS specify context
kubectl --context=fbg-inf-dev-1 get tests -n testkube
kubectl --context=fbg-inf-dev-1 get pods -n testkube
```

#### TestKube Execution Best Practices

- **Always use proxy client mode** when working locally with TestKube CLI
- **Set kubectl context first** before configuring testkube to ensure proper cluster targeting
- **Use --watch flag** to see real-time test output and logs
- **Verify branch targeting** in test YAML files when developing new tests (should point to feature branch)
- **TestWorkflows use Amazon Linux base image** from `public.ecr.aws/amazonlinux/amazonlinux:2`
- **SSM credentials** are automatically fetched using service account IAM roles - never hardcode them

### PGBouncer Configuration

- **Service**: `pgbouncer-ats` in `fbg-inf-dev-1` namespace on port 5432
- **Authentication**: Uses AWS IAM roles and SSM Parameter Store (not username/password)
- **Configuration**: Managed via confd containers reading from AWS SSM
- **AWS Role**: `arn:aws:iam::222019643140:role/eks-application-iam-pgbouncer-role`
- **SSM Parameters**: Environment-specific paths resolved by Flux/Kustomize:
  - `/${ENVIRONMENT_NAME}/pgbouncer-ats/db-username`
  - `/${ENVIRONMENT_NAME}/pgbouncer-ats/db-password`

### TestKube Web UI

Access tests via: https://testkube.cicd.fanatics.bet/clusters/inf-dev-1/tests

## Performance Testing Documentation

- **Main Guide**: [TestKube Deployment and Testing Guide](../docs/deployment-guide.md)
  - Complete deployment process from code to execution
  - Test vs TestWorkflow CRD differences
  - GitHub Actions integration
  - Authentication patterns (SSM, service accounts)
  - Troubleshooting and best practices

- **Service-Specific Guides**:
  - [PGBouncer Tests](../tests/pgbouncer/README.md) - Database connection stability testing
  - [Common Utils](../docs/commonutils.md) - Shared test utilities
  - [Test Profile Setup](../docs/testProfileSetUp.md) - Environment-specific configurations
