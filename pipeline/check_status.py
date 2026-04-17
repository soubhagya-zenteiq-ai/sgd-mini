import kfp
import os
import sys
import time

def check_run_status(run_id):
    host = os.getenv('KUBEFLOW_ENDPOINT', 'http://localhost:8080')
    client = kfp.Client(host=host)
    
    print(f"🧐 Checking status for run: {run_id}")
    
    while True:
        run = client.get_run(run_id)
        status = run.state
        print(f"Current State: {status}")
        
        if status in ['SUCCEEDED', 'FAILED', 'SKIPPED', 'CANCELLED', 'Error']:
            print(f"🏁 Run finished with status: {status}")
            break
            
        time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_status.py <run_id>")
        sys.exit(1)
    
    check_run_status(sys.argv[1])
