import subprocess
import argparse
import textwrap
import json
import os
from datetime import UTC, datetime
from settings import get_settings
from kafka_client import create_kafka_producer
from logger import get_logger

type_map = {
    "GlanceImages.create_and_delete_image": "compute",
    "GlanceImages.list_images": "compute",
    "CinderVolumes.create_and_delete_volume": "block-storage",
    "CinderVolumes.create_and_attach_volume": "block-storage",
    "NeutronNetworks.associate_and_dissociate_floating_ips": "networking",
    "NeutronSecurityGroup.create_and_delete_security_group_rule": "networking",
    "NeutronSecurityGroup.create_and_delete_security_groups": "networking",
    "NovaFlavors.list_flavors": "compute",
    "NovaKeypair.create_and_delete_keypair": "compute",
}


def write_env_file(logger, path, auth_url, region_name, user, password, project):
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
    """).lstrip()
    with open(path, "w") as f:
        f.write(content)


def write_args_file(
    logger, path, flavor_name, public_net, floating_ips_enable, cinder_net_id=None
):
    """Writes the OpenStack args YAML spec to the given path"""
    lines = [
        "---",
        "service_list:",
        "  - nova",
        "  - neutron",
        "  - cinder",
        "  - glance",
        "use_existing_users: true",
        'glance_image_location: "./rally-data/cirros-0.6.1-x86_64-disk.img"',
        'image_name: "^(cirros-0.6.1|cirros|infn-cloud-mon)$"',
        "smoke: true",
        "users_amount: 1",
        "tenants_amount: 1",
        f'flavor_name: "{flavor_name}"',
        f'neutron_floating_network: "{public_net}"',
        f"floating_ips_enable: {str(floating_ips_enable)}",
    ]
    if cinder_net_id:
        lines.append(f'cinder_net_id: "{cinder_net_id}"')
    content = "\n".join(lines) + "\n"
    with open(path, "w") as f:
        f.write(content)
    logger.debug(f"Wrote environment specification to {path}")


def collect_data(report, msg_version):
    json_data = json.loads(report)
    record = dict()
    record["msg_version"] = msg_version
    record["provider_name"] = json_data["tasks"][0]["env_name"]
    record["provider_type"] = json_data["tasks"][0]["tags"][0]
    record["status"] = json_data["tasks"][0]["status"]
    record["success"] = str(json_data["tasks"][0]["pass_sla"])
    substasks = []
    for st in json_data["tasks"][0]["subtasks"]:
        wl = st["workloads"][0]
        subtask_record = {
            "type": type_map.get(st["title"], "unknown"),
            "title": st["title"],
            "status": st["status"],
            "success": str(wl["pass_sla"]),
            "elapsed_time": wl["full_duration"],
            "failed_iteration_count": wl["failed_iteration_count"],
            "total_iteration_count": wl["total_iteration_count"],
        }
        substasks.append(subtask_record)
    record["subtasks"] = substasks
    record["timestamp"] = datetime.now(UTC).isoformat()
    return record


def execute_rally(args, settings, logger):
    logger.info(f"Starting rally execution for provider {args['provider_name']}")
    providerName = args["provider_name"]
    providerType = args["provider_type"]
    taskFile = os.path.join("./rally-data/", "task.yaml")
    envFile = os.path.join(settings.RALLY_ENVS_FOLDER, f"env_{providerName}.yaml")
    argsFile = os.path.join(
        settings.RALLY_ARGS_FOLDER, f"args_task_{providerName}.yaml"
    )
    reportFile = os.path.join(
        settings.RALLY_REPORT_FOLDER, f"report_{providerName}.json"
    )

    # Write env file
    write_env_file(
        logger=logger,
        path=envFile,
        auth_url=args["auth_url"],
        region_name=args["region"],
        user=args["user"],
        password=args["password"],
        project=args["project"],
    )
    # Write args file
    write_args_file(
        logger=logger,
        path=argsFile,
        flavor_name=args["flavor_name"],
        public_net=args["public_net"],
        floating_ips_enable=args["floating_ips_enable"],
        cinder_net_id=args["cinder_net_id"],
    )

    # Create OpenStack Env
    subprocess.run(["rally", "db", "create"])
    subprocess.run(
        ["rally", "env", "create", "--name", providerName, "--spec", envFile]
    )

    # Check that you provide correct credentials
    subprocess.run(["rally", "env", "check"])

    # Collect key Open Stack metrics
    subprocess.run(
        [
            "rally",
            "task",
            "start",
            taskFile,
            "--task-args-file",
            argsFile,
            "--tag",
            providerType,
        ]
    )

    # Generate Report
    subprocess.run(["rally", "task", "report", "--json", "--out", reportFile])
    message = subprocess.run(
        ["rally", "task", "report", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )

    # Delete Env
    subprocess.run(["rally", "env", "destroy", "--env", providerName])
    subprocess.run(["rally", "env", "delete", "--env", providerName, "--force"])

    # Get the report and convert to json
    report = message.stdout
    report_data = collect_data(report, settings.KAFKA_MSG_VERSION)
    logger.debug(f"Collected report data: {report_data}")

    # Send results to Kafka
    if settings.KAFKA_ENABLE:
        producer = create_kafka_producer(settings=settings, logger=logger)
        producer.send(settings.KAFKA_TOPIC, report_data)
        producer.flush()
        producer.close()
        logger.info(
            "Message sent to topic "
            + settings.KAFKA_TOPIC
            + " of kafka server "
            + settings.KAFKA_BOOTSTRAP_SERVERS
        )
    return report_data


def main():
    settings = get_settings()
    logger = get_logger(settings)
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider_name", required=True, help="Provider name")
    parser.add_argument("--provider_type", required=True, help="Provider type")
    parser.add_argument("--auth_url", required=True, help="OpenStack Keystone URL")
    parser.add_argument("--region", required=True, help="OpenStack region name")
    parser.add_argument(
        "--user", required=True, help="OpenStack user that runs commands"
    )
    parser.add_argument("--password", required=True, help="Password of the user")
    parser.add_argument(
        "--project", required=True, help="Project that the user belongs to"
    )
    parser.add_argument(
        "--flavor_name", default="tiny", help="Name of the favour to use"
    )
    parser.add_argument(
        "--public_net", default="public", help="Name of the public network"
    )
    parser.add_argument(
        "--floating_ips_enable", required=True, help="If floating IPs are enabled"
    )
    parser.add_argument(
        "--cinder_net_id", default=None, help="If floating IPs are enabled"
    )
    args = parser.parse_args()
    report_data = execute_rally(vars(args), settings=settings, logger=logger)
    logger.info(f"Rally execution completed with report data: {report_data}")


if __name__ == "__main__":
    main()
