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


def get_project(url, headers, params, timeout, provider_id):
    url = f"{url}providers/{provider_id}/projects/"
    res = requests.get(
        url, headers=headers, params={**params, "is_root": True}, timeout=timeout
    )
    res.raise_for_status()
    return res.json()["data"][0]["name"]


def decrypt(password):
    # Placeholder for decryption logic
    return password


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
        if provider["status"] in settings.REQUESTED_PROVIDER_STATUS:
            project = get_project(url, headers, params, timeout, provider["id"])
            regions = get_regions(url, headers, params, timeout, provider["id"])
            for region in regions:
                success = False
                report_data = execute_rally(
                    args={
                        "provider_name": provider["name"],
                        "provider_type": provider["type"],
                        "auth_url": provider["auth_endpoint"],
                        "region": region["name"],
                        "user": provider["rally_username"],
                        "password": decrypt(provider["rally_password"]),
                        "project": project["iaas_project_id"],
                        "flavor_name": provider["image_tags"][0]
                        if provider.get("image_tags")
                        else "tiny",
                        "public_net": provider["public_net"][0]
                        if provider.get("public_net")
                        else "public",
                        "floating_ips_enable": "true"
                        if provider.get("is_public")
                        else "false",
                        "cinder_net_id": provider["network_tags"][0]
                        if provider.get("network_tags")
                        and len(provider["network_tags"]) > 0
                        and provider["network_tags"][0] is not None
                        else None,
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
