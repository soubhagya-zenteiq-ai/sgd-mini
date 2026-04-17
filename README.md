# SGD-Mini RAG Pipeline

This is an end-to-end Kubeflow pipeline for processing markdown files into a detailed knowledge base and structured QAs using a local GGUF model.

## 🚀 Quick Start Guide

### 1. Initialize Kubernetes (Minikube)
Start minikube with sufficient resources for the LLM component:
```bash
minikube start --memory=8192 --cpus=4
```

### 2. Configure Minikube Registry
Enable the internal registry and forward the port so your local Docker can push to it. **Keep this port-forward running in a separate terminal:**
```bash
# Enable minikube registry
minikube addons enable registry

# Forward registry port to localhost:5000
kubectl port-forward --namespace kube-system service/registry 5000:80
```

### 3. Setup Persistent Infrastructure
Apply the Persistent Volume configuration and mount your local directories into the Minikube node. **Keep these mounts running in separate terminals:**

```bash
# Apply Volumes & PVCs
kubectl apply -f infra/sgd-volumes.yaml

# Apply Database (PostgreSQL)
kubectl apply -f infra/postgres.yaml

# Mount Data Folder
minikube mount /home/zenteiq/Documents/sgd-mini/data:/mnt/data

# Mount Models Folder
minikube mount /home/zenteiq/Documents/sgd-mini/models:/mnt/models
```

### 4. Setup Local Environment
Install the required tools for pipeline compilation and submission:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 5. Build & Push Images
Build the component images and push them to the local registry:
```bash
# Ingestion
cd components/ingestion
docker build -t localhost:5000/sgd-ingestion:latest .
docker push localhost:5000/sgd-ingestion:latest
cd ../..

# LLM Processor
cd components/llm_processor
docker build -t localhost:5000/sgd-llm-processor:latest .
docker push localhost:5000/sgd-llm-processor:latest
cd ../..

# Storage
cd components/storage
docker build -t localhost:5000/sgd-storage:latest .
docker push localhost:5000/sgd-storage:latest
cd ../..
```

### 6. Submit the Pipeline
Forward the Kubeflow UI port and submit the run using the SDK.

```bash
# Forward Kubeflow UI (Keep running in a separate terminal)
kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8080:80

# Activate venv, compile, and submit
source .venv/bin/activate
python3 pipeline/compiler.py
python3 pipeline/submit_run.py
```

## 📂 Directory Structure
- `components/`: Source code and Dockerfiles for each pipeline stage.
- `pipeline/`: Pipeline definition, compiler, and submission scripts.
- `infra/`: Kubernetes YAMLs for volumes and storage.
- `data/`: Local storage for source documents.
- `models/`: Local storage for GGUF models.

## 🛠 Configuration
- **Model**: Default model is `LFM2.5-1.2B-Instruct-Q8_0.gguf`. Place it in your local `models/` folder.
- **Paths**: The pipeline expects the model at `/mnt/models/LFM2.5-1.2B-Instruct-Q8_0.gguf` inside the pod.

Detailed flow information can be found in [INFO.md](INFO.md).
If you encounter any issues with Minikube, registry connectivity, or pipeline execution, please refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
