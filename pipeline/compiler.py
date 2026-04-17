from kfp import compiler
from pipeline_definition import sgd_pipeline
import os

def compile_pipeline():
    output_path = 'sgd_pipeline_spec.yaml'
    compiler.Compiler().compile(
        pipeline_func=sgd_pipeline,
        package_path=output_path
    )
    print(f"Pipeline compiled to {output_path}")

if __name__ == "__main__":
    compile_pipeline()
