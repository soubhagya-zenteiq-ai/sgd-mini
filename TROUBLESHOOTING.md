# Troubleshooting Guide

This document catalogs common issues encountered while setting up and running the SGD-Mini RAG Pipeline on Minikube, along with their solutions.

## 1. Connection Refused when Submitting Pipeline Runs
**Error:** `Failed to establish a new connection: [Errno 111] Connection refused` in `submit_run.py`.
**Cause:** The script needs to communicate with the Kubeflow Pipeline UI API on `localhost:8080`, but the port is not forwarded.
**Solution:** Run the port-forwarding command in a background terminal before submitting:
```bash
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8080:80
```

## 2. Docker Push Fails (Connection Refused to Registry)
**Error:** `docker push localhost:5000/sgd-...` fails with connection refused.
**Cause:** Minikube hosts its registry internally, and your host Docker daemon cannot reach it without a bridge.
**Solution:**
1. Enable the minikube registry addon: `minikube addons enable registry`
2. Forward the registry port from Minikube to your host:
```bash
kubectl port-forward --namespace kube-system service/registry 5000:80
```

## 3. Pods Stuck in "Pending" (Insufficient Memory)
**Error:** Using `kubectl describe pod <pod-name> -n kubeflow` shows:
`Warning  FailedScheduling  0/1 nodes are available: 1 Insufficient memory.`
**Cause:** Minikube was started with insufficient memory, preventing the LLM processor or other components from scheduling due to their resource requests.
**Solution:**
1. Increase Minikube memory constraints: `minikube start --memory=8192 --cpus=4` (or `16384` if available).
2. Alternatively, lower the `memory_request` inside `pipeline/pipeline_definition.py`:
```python
process.set_cpu_request("2")
process.set_memory_request("4Gi")
```

## 4. Component Error: `TypeError: unsupported operand type(s) for |`
**Error:** You see the following in the component logs:
`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
**Cause:** Python 3.9 does not support the `|` syntax for Union types natively (introduced in 3.10), and the component is running on `python:3.9-slim`.
**Solution:** Modify `extract_json` to use `typing.Optional`:
```python
from typing import Optional
def extract_json(text: str) -> Optional[str]:
```

## 5. Components Reusing Old Code After Rebuild
**Error:** You rebuilt and pushed the Docker images to fix a bug, but the new pipeline run still fails with the same exact error.
**Cause:** The Kubernetes cluster is using the `IfNotPresent` pull policy. Because the image `latest` is already on the node, it does not fetch the new update.
**Solution:** Modify `pipeline_definition.py` to force KFP to pull the fresh image every time:
```python
kubernetes.set_image_pull_policy(process, 'Always')
```

## 6. Debugging Pipeline Failures
If the pipeline triggers successfully but a stage enters the `Error` status, check the Argo pod logs:
```bash
# Get the exact pod name
kubectl get pods -n kubeflow | grep sgd-kb-qa-pipeline

# View logs for the main container (replace <pod-name>)
kubectl logs <pod-name> -n kubeflow -c main

# Enter the pod interactively
kubectl exec -it -n kubeflow deploy/postgres -- psql -U user -d sgd_db

# OR run a quick query to see the Knowledge Base entries
kubectl exec -it -n kubeflow deploy/postgres -- psql -U user -d sgd_db -c "SELECT * FROM knowledge_base;"

# OR see the generated QAs
kubectl exec -it -n kubeflow deploy/postgres -- psql -U user -d sgd_db -c "SELECT * FROM qas LIMIT 10;"
```
