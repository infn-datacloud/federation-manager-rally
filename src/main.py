import requests
from logger import get_logger
from script import execute_rally
from settings import get_settings


def get_providers(url, headers, params, timeout):
    url = f"{url}providers/"
    res = requests.get(url, headers=headers, params=params, timeout=timeout)
    res.raise_for_status()
    return res.json()["data"]


def get_regions(url, headers, params, timeout, provider_id):
    url = f"{url}providers/{provider_id}/regions/"
    res = requests.get(url, headers=headers, params=params, timeout=timeout)
    res.raise_for_status()
    return res.json()["data"]


def get_region_overrides(
    url, headers, params, timeout, provider_id, project_id, region_id
):
    url = f"{url}providers/{provider_id}/projects/{project_id}/regions/{region_id}"
    res = requests.get(url, headers=headers, params=params, timeout=timeout)
    if res.status_code == 404:
        return {}
    res.raise_for_status()
    return res.json()["overrides"]


def get_project(url, headers, params, timeout, provider_id):
    url = f"{url}providers/{provider_id}/projects/"
    res = requests.get(
        url, headers=headers, params={**params, "is_root": True}, timeout=timeout
    )
    res.raise_for_status()
    return res.json()["data"][0]["name"]


def decrypt(password, fernet):
    return fernet.decrypt(password.encode()).decode()


def run_script(settings, logger):
    url = settings.FED_MGR_API_URL
    headers = {"accept": "application/json", "X-API-Key": settings.X_API_KEY}
    params = {
        "sort": "-created_at",
        "size": settings.API_SIZE,
        "page": settings.API_PAGE,
    }
    timeout = settings.API_TIMEOUT
    providers = get_providers(url, headers, params, timeout)
    for provider in providers:
        if provider["status_name"] in settings.REQUESTED_PROVIDER_STATUS:
            project = get_project(url, headers, params, timeout, provider["id"])
            regions = get_regions(url, headers, params, timeout, provider["id"])
            for region in regions:
                overrides = get_region_overrides(
                    url,
                    headers,
                    params,
                    timeout,
                    provider["id"],
                    project["id"],
                    region["id"],
                )
                success = False
                report_data = execute_rally(
                    args={
                        "provider_name": provider["name"],
                        "provider_type": provider["type"],
                        "auth_url": provider["auth_endpoint"],
                        "region": region["name"],
                        "user": provider["rally_username"],
                        "password": decrypt(
                            provider["rally_password"], settings.SECRET_KEY
                        ),
                        "project": project["iaas_project_id"],
                        "flavor_name": provider["test_flavor_name"],
                        "public_net": overrides.get("default_public_net", "public"),
                        "floating_ips_enable": provider.get(
                            "floating_ips_enable", False
                        ),
                        "cinder_net_id": provider["test_network_id"],
                    }
                )
                status = report_data.get("status")
                pass_sla = report_data.get("success") == "True"
                success = status == "finished" and pass_sla
                logger.info(
                    f"Rally test {'succeeded' if success else 'failed'} for provider "
                    + f"{provider['name']} in region {region['name']}"
                )


def main():
    settings = get_settings()
    logger = get_logger(settings)
    run_script(settings, logger)


if __name__ == "__main__":
    main()
