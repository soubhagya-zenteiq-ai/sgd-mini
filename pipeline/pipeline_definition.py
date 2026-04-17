from kfp import dsl
from kfp import kubernetes
from kfp.dsl import Dataset, Input, Output, Artifact, Model

# --- Component Definitions ---

@dsl.container_component
def ingestion_op(
    input_dir: str,
    output_json: Output[Dataset]
):
    return dsl.ContainerSpec(
        image='localhost:5000/sgd-ingestion:latest',
        command=['python', 'src/main.py'],
        args=[
            '--input_dir', input_dir,
            '--output_file', output_json.path
        ]
    )

@dsl.container_component
def llm_processor_op(
    input_json: Input[Dataset],
    model_path: str,
    output_kb: Output[Artifact],
    output_qa: Output[Dataset]
):
    return dsl.ContainerSpec(
        image='localhost:5000/sgd-llm-processor:latest',
        command=['python', 'src/main.py'],
        args=[
            '--input_file', input_json.path,
            '--model_path', model_path,
            '--output_kb', output_kb.path,
            '--output_qa', output_qa.path
        ]
    )

@dsl.container_component
def storage_op(
    kb_file: Input[Artifact],
    qa_file: Input[Dataset],
    storage_type: str = 'both'
):
    return dsl.ContainerSpec(
        image='localhost:5000/sgd-storage:latest',
        command=['python', 'src/main.py'],
        args=[
            '--kb_file', kb_file.path,
            '--qa_file', qa_file.path,
            '--storage_type', storage_type
        ]
    )

# --- Pipeline Definition ---

@dsl.pipeline(
    name='sgd-kb-qa-pipeline',
    description='Pipeline to process MD files into a knowledge base and QAs using an LLM.'
)
def sgd_pipeline(
    input_dir: str = '/mnt/data/md-files',
    model_path: str = '/mnt/models/LFM2.5-1.2B-Instruct-Q8_0.gguf',
    storage_type: str = 'both',
    data_pvc: str = 'sgd-data-pvc',
    models_pvc: str = 'sgd-models-pvc'
):
    # 1. Ingestion
    ingest = ingestion_op(input_dir=input_dir)
    ingest.set_caching_options(False)
    kubernetes.set_image_pull_policy(ingest, 'Always')
    kubernetes.mount_pvc(
        ingest,
        pvc_name=data_pvc,
        mount_path='/mnt/data'
    )

    # 2. LLM Processing
    process = llm_processor_op(
        input_json=ingest.outputs['output_json'],
        model_path=model_path
    )
    process.set_caching_options(False)
    kubernetes.set_image_pull_policy(process, 'Always')
    
    # Resource requests for LLM
    process.set_cpu_request("2")
    process.set_memory_request("4Gi")

    kubernetes.mount_pvc(
        process,
        pvc_name=models_pvc,
        mount_path='/mnt/models'
    )

    # 3. Storage
    save = storage_op(
        kb_file=process.outputs['output_kb'],
        qa_file=process.outputs['output_qa'],
        storage_type=storage_type
    )
    save.set_caching_options(False)
    kubernetes.set_image_pull_policy(save, 'Always')
    
    # Inject DB and MinIO configuration
    save.set_env_variable(
        name='DATABASE_URL',
        value='postgresql://user:password@postgres-service.kubeflow.svc.cluster.local:5432/sgd_db'
    )
    save.set_env_variable(
        name='MINIO_ENDPOINT',
        value='http://minio-service.kubeflow.svc.cluster.local:9000'
    )
    save.set_env_variable(
        name='MINIO_ACCESS_KEY',
        value='minioadmin'
    )
    save.set_env_variable(
        name='MINIO_SECRET_KEY',
        value='minioadmin'
    )
