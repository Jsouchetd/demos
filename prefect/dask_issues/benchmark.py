from prefect import Flow, task
from prefect.executors import DaskExecutor
from dask_kubernetes import KubeCluster, make_pod_spec
from prefect.storage import GitHub
from prefect.run_configs import KubernetesRun
import prefect
from prefect.engine.state import State
from typing import Set, Optional
import io
from prefect.utilities.aws import get_boto_client
import prefect

def custom_terminal_state_handler(
    flow: Flow,
    state: State,
    reference_task_states: Set[State],
) -> Optional[State]:
    prefect.context.logger.info("AM AT TERMINAL STATE HANDLER")
    report = flow.executor.performance_report
    s3_client = get_boto_client("s3")
    report_data = io.BytesIO(report.encode())
    prefect.context.logger.info("UPLOADING THE PERFORMANCE REPORT")
    s3_client.upload_fileobj(report_data, Bucket="coiled-prefect", Key="performance_report.html")
    prefect.context.logger.info("DONE UPLOADING")

@task
def do_nothing(n):
    pass

items = list(range(8000))

with Flow("map_testing") as flow:
    do_nothing.map(items)
    
executor=DaskExecutor(
        cluster_class=lambda: KubeCluster(make_pod_spec(image="prefecthq/prefect",
        env={'EXTRA_PIP_PACKAGES': "bokeh"}, memory_request='4G', memory_limit='4G', threads_per_worker=4)),
        cluster_kwargs={"n_workers": 5},
        debug=True,
        performance_report_path="performance_report.html",
        client_kwargs=dict(set_as_default=True)
    )
flow.executor = executor
flow.run_config = KubernetesRun(env={"EXTRA_PIP_PACKAGES": "dask_kubernetes boto3 bokeh"})
flow.storage = GitHub(repo="kvnkho/demos", path="prefect/dask_issues/benchmark.py", secrets=["AWS_CREDENTIALS"])
flow.terminal_state_handler = custom_terminal_state_handler
flow.register("dask_issue")
