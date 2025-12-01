# scripts/autoscale.py
"""
Autoscaler (AWS EC2 example)
- Reads queue length (via DB or TASKS_DIR) and decides to spin up worker instances (EC2) with a given launch-template.
- Uses IAM roles (recommended). Keep this as helper and adapt to your infra.
"""
import os, boto3, time, math
from pathlib import Path

AWS_REGION = os.getenv("AWS_REGION","us-east-1")
LAUNCH_TEMPLATE_ID = os.getenv("LAUNCH_TEMPLATE_ID")  # prebuilt launch template with worker image + tags
MAX_INSTANCES = int(os.getenv("SCALE_MAX", "6"))
MIN_INSTANCES = int(os.getenv("SCALE_MIN", "0"))
QUEUE_THRESH_UP = int(os.getenv("QUEUE_UP", "50"))
QUEUE_THRESH_DOWN = int(os.getenv("QUEUE_DOWN", "10"))

ec2 = boto3.client("ec2", region_name=AWS_REGION)

def get_pending_tasks_count():
    # Example: look at TASKS_DIR length — switch to DB count if using Postgres
    TASKS_DIR = Path("jobs/farm/tasks")
    if TASKS_DIR.exists():
        return len(list(TASKS_DIR.glob("*.json")))
    return 0

def get_worker_instances():
    resp = ec2.describe_instances(Filters=[{"Name":"tag:Role","Values":["farm-worker"]}, {"Name":"instance-state-name","Values":["running","pending"]}])
    instances = []
    for r in resp['Reservations']:
        for i in r['Instances']:
            instances.append(i)
    return instances

def scale():
    pending = get_pending_tasks_count()
    workers = get_worker_instances()
    nw = len(workers)
    print("Pending:", pending, "Workers:", nw)
    if pending > QUEUE_THRESH_UP and nw < MAX_INSTANCES:
        # scale up: launch one instance
        resp = ec2.run_instances(LaunchTemplate={"LaunchTemplateId": LAUNCH_TEMPLATE_ID, "Version":"$Default"}, MinCount=1, MaxCount=1)
        print("Launched instance:", resp['Instances'][0]['InstanceId'])
    elif pending < QUEUE_THRESH_DOWN and nw > MIN_INSTANCES:
        # scale down: pick an instance with low load and terminate (careful!)
        iid = workers[0]['InstanceId']
        ec2.terminate_instances(InstanceIds=[iid])
        print("Terminated instance:", iid)

if __name__ == "__main__":
    # run once or loop in cron
    scale()
