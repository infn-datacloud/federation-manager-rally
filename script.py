import subprocess
import argparse
import textwrap
import json
from datetime import datetime
from settings import get_settings
from kafka_client import create_kafka_producer

def write_env_file(path, auth_url, region_name, user, password, project):
    """Writes the OpenStack environment YAML spec to the given path"""
    content = textwrap.dedent(f"""
    ---
    openstack:
      auth_url: "{auth_url}"
      region_name: {region_name}
      https_insecure: False
      users:
        - username: {user}
          password: {password}
          project_name: {project}
    """
    ).lstrip()
    with open(path, 'w') as f:
        f.write(content)
    print(f"Wrote environment specification to {path}")

def write_args_file(path, flavor_name, public_net, floating_ips_enable, cinder_net_id=None):
    """Writes the OpenStack args YAML spec to the given path"""
    lines = [
        '---',
        'service_list:',
        '  - nova',
        '  - neutron',
        '  - cinder',
        '  - glance', 
        'use_existing_users: true',
        'glance_image_location: "./data/cirros-0.6.1-x86_64-disk.img"',
        'image_name: "^(cirros-0.6.1|cirros|infn-cloud-mon)$"',
        'smoke: true',
        'users_amount: 1',
        'tenants_amount: 1',
        f'flavor_name: "{flavor_name}"',
        f'neutron_floating_network: "{public_net}"',
        f'floating_ips_enable: {str(floating_ips_enable)}'
    ]
    if cinder_net_id:
        lines.append(f'cinder_net_id: "{cinder_net_id}"')
    content = '\n'.join(lines) + '\n'
    with open(path, 'w') as f:
        f.write(content)
    print(f"Wrote environment specification to {path}")

def collect_data(message, msg_version):
    report = message.stdout 
    json_data = json.loads(report)
    str_ts = json_data['info']['generated_at']
    ts = datetime.strptime(str_ts, '%Y-%m-%dT%H:%M:%S')
    record = dict()
    record['timestamp'] = str_ts
    record['msg_version'] = msg_version
    record['status'] = json_data['tasks'][0]['status']
    record['tag'] = json_data['tasks'][0]['tags'][0]
    record['provider'] = json_data['tasks'][0]['env_name']
    record['test_result'] = str(json_data['tasks'][0]['pass_sla'])
    return record

def main():
    settings = get_settings()
   
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider_name', required=True, help='Provider name')
    parser.add_argument('--auth_url', required=True, help='OpenStack Keystone URL')
    parser.add_argument('--region', required=True, help='OpenStack region name')
    parser.add_argument('--user', required=True, help='OpenStack user that runs commands')
    parser.add_argument('--password', required=True, help='Password of the user')
    parser.add_argument('--project', required=True, help='Project that the user belongs to')
    parser.add_argument('--flavor_name', default='tiny', help='Name of the favour to use')
    parser.add_argument('--public_net', default='public', help='Name of the public network')
    parser.add_argument('--floating_ips_enable', required=True, help='If floating IPs are enabled')
    parser.add_argument('--cinder_net_id', default=None, help='If floating IPs are enabled')
    args = parser.parse_args()

    providerName = args.provider_name
    envFile = './env_' + providerName + '.yaml'
    argsFile = './data/args_task_' + providerName + '.yaml'
    reportFile = './data/reports/report_' + providerName + '.json'

    # Write env file
    write_env_file(
        path=envFile,
        auth_url=args.auth_url,
        region_name=args.region,
        user=args.user,
        password=args.password,
        project=args.project
    )
    # Write args file
    write_args_file(
        path=argsFile,
        flavor_name=args.flavor_name,
        public_net=args.public_net, 
        floating_ips_enable=args.floating_ips_enable, 
        cinder_net_id=args.cinder_net_id
    )
    
    # Create OpenStack Env
    subprocess.run(['rally', 'db', 'create'])
    subprocess.run(['rally', 'env', 'create', '--name', providerName, '--spec', envFile])

    # Check that you provide correct credentials
    subprocess.run(['rally', 'env', 'check'])

    # Collect key Open Stack metrics
    subprocess.run(['rally', 'task', 'start', './data/task.yaml', '--task-args-file', argsFile, '--tag', 'test-rally'])
    
    # Generate Report
    subprocess.run(['rally', 'task', 'report', '--json', '--out', reportFile])
    message = subprocess.run(
        ['rally', 'task', 'report', '--json'],
        capture_output=True,
        text=True,
        check=True
    )

    # Delete Env
    subprocess.run(['rally', 'env', 'destroy', '--env', providerName])
    subprocess.run(['rally', 'env', 'delete', '--env', providerName, '--force'])

    # Get the report and convert to json 
    report_data = collect_data(message, settings.KAFKA_MSG_VERSION)

    # Send results to Kafka
    producer = create_kafka_producer(settings=settings)
    producer.send(settings.KAFKA_TOPIC, report_data)
    producer.flush()
    producer.close()
    print(
        'Message sent to topic ' + settings.KAFKA_TOPIC + ' of kafka server ' + settings.KAFKA_BOOTSTRAP_SERVERS
    )


if __name__ == '__main__':
    main()
