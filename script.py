import subprocess

def main():
    
    # Create OpenStack Env
    subprocess.run(['rally', 'db', 'create'])
    subprocess.run(['rally', 'env', 'create', '--name', 'test', '--spec', './env.yaml'])

    # Check that you provide correct credentials
    subprocess.run(['rally', 'env', 'check'])

    # Collect key Open Stack metrics
    subprocess.run(['rally', 'task', 'start', './data/task.yaml', '--task-args-file', './data/args_task.yaml'])
    
    # Generate Report
    subprocess.run(['rally', 'task', 'report', '--json', '--out', './data/reports/report.json'])
    
    # Delete Env
    subprocess.run(['rally', 'env', 'destroy', '--env', 'test'])
    subprocess.run(['rally', 'env', 'delete', '--env', 'test'])


if __name__ == '__main__':
    main()
