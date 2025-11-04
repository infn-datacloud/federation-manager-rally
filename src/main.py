import requests
from script import execute_rally

params = {"sort": "-created_at", "size": 5, "page": 1}
headers = {"accept": "application/json", "X-API-Key": "alessandra"}


def get_providers():
    url = "http://localhost:8000/api/v1/providers/"
    res = requests.get(url, headers=headers, params=params, timeout=15)
    res.raise_for_status()
    return res.json()["data"]


def get_regions(provider_id):
    url = f"http://localhost:8000/api/v1/providers/{provider_id}/regions/"
    res = requests.get(url, headers=headers, params=params, timeout=15)
    res.raise_for_status()
    return res.json()["data"]


def get_project(provider_id):
    url = f"http://localhost:8000/api/v1/providers/{provider_id}/projects/"
    res = requests.get(
        url, headers=headers, params={**params, "is_root": True}, timeout=15
    )
    res.raise_for_status()
    return res.json()["data"][0]["name"]


def run_script(providers):
    for provider in providers:
        if provider["status"] in [3, 4, 5, 6, 8, 9, 10]:
            project = get_project(provider["id"])
            regions = get_regions(provider["id"])
            for region in regions:
                success = False
                for i in range(3):
                    try:
                        report_data = execute_rally(
                            args={
                                "provider_name": provider["name"],
                                "provider_type": provider["type"],
                                "auth_url": provider["auth_endpoint"],
                                "region": region["name"],
                                "user": provider["rally_username"],
                                "password": "1234",  # decript function
                                "project": project,
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
                        pass_sla = report_data.get("success") in ["True", True]
                        success = status == "finished" and pass_sla
                        if success:
                            break
                    except Exception as e:
                        print(f"Attempt {i + 1} failed: {e}")
                if not success:
                    print(
                        "Rally test failed for provider "
                        + provider["name"]
                        + " in region "
                        + region["name"]
                    )
                else:
                    print(
                        "Rally test succeeded for provider "
                        + provider["name"]
                        + " in region "
                        + region["name"]
                    )


def main():
    providers = get_providers()
    run_script(providers)


if __name__ == "__main__":
    main()
