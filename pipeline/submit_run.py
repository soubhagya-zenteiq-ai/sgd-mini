import kfp
import os

def submit_sgd_pipeline():
    # Attempt to use KUBEFLOW_ENDPOINT env var or default to local port-forwarding
    host = os.getenv('KUBEFLOW_ENDPOINT', 'http://localhost:8080')
    pipeline_spec = 'sgd_pipeline_spec.yaml'
    
    client = kfp.Client(host=host)
    
    print(f"🚀 Submitting pipeline '{pipeline_spec}' to Kubeflow at {host}...")
    
    arguments = {
        'input_dir': '/mnt/data',
        'model_path': '/mnt/models/LFM2.5-1.2B-Instruct-Q8_0.gguf',
        'storage_type': 'both',
        'data_pvc': 'sgd-data-pvc',
        'models_pvc': 'sgd-models-pvc'
    }
    
    try:
        run = client.create_run_from_pipeline_package(
            pipeline_file=pipeline_spec,
            arguments=arguments,
            run_name='sgd-mini-automated-run'
        )
        print(f"✅ Success! Run created with ID: {run.run_id}")
        print(f"🔗 Monitor the run at: {host}/#/runs/details/{run.run_id}")
    except Exception as e:
        print(f"❌ Failed to submit run: {e}")
        print("\nTIP: Make sure you have port-forwarded the Kubeflow service:")
        print("kubectl port-forward svc/ml-pipeline-ui -n kubeflow 8080:80")

if __name__ == "__main__":
    submit_sgd_pipeline()
