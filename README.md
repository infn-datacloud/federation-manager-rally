# Federation-Manager Rally

The Federation-Manager Rally is an application, written in python, used to run Rally tests on providers (at the moment only OpenStack) to check their readiness to be federated as new resource provider.

The Rally tests are based on [Rally](https://rally.readthedocs.io) commands and derived from th [rally_openstack repository](https://github.com/openstack/rally-openstack/tree/master/rally_openstack/task/scenarios). The Openstack services that are tested are:
- Nova: list of OpenStack flavors, creation-elimination of a keypair.
- Neutron: association-dissociation of floating ips, creation-elimination of security groups and security group rule.
- Glance: list of images, creation-elimination of an image.
- Cinder: creation-elimination and creation-attachment of a volume.
The user authentication and token validation of the Keystone service are implied in these tests.

The application is also designed to communicate with:
- Federation Manager REST API to collect information regarding the providers to test.
- Kafka to send the Rally test results.

A docker image for this service is available on INFN Cloud's harbor [harbor.cloud.infn.it/datacloud-middleware/fed-mgr-rally](harbor.cloud.infn.it/datacloud-middleware/fed-mgr-rally).

## Run the application

### Local mode

Requirements:
- python >= 3.13.
- [poetry](https://python-poetry.org/) >= 2.1

If you want to run the application directly on your host, you must at first configure your environment. These steps must be executed only the first time you clone this repository:

- Install the needed python packages using poetry
  
  ```bash
  poetry install --without dev --no-root
  ```

  This command will install the required python packages. It generates a `.venv` directory in your workspace directory (not tracked by git). 

- Activate the generated virtualenv

  ```bash
  poetry env activate 
  ```

- Create a `.env` file and add to it the required environment variables. You can rename the `.env.example` file and change it for your needs. 

  For a list of available environment variables see the [Environment variables](#environment-variables) section.

Once your environment has been correctly configured you can start the application.

```bash
poetry run python src/script.py /
--provider_name my_cloud_name /
--provider_type openstack /
--provider_id my_cloud_id /
--auth_url https://my_auth.infn.it:443/v3 /
--region my_region /
--user my_username /
--password my_pwd /
--project my_project /
--floating_ips_enable True 
--cinder_net_id my_net_id
```

Details on input variables are described in the section [Config variables](#config-variables)


### Container mode

Requirements:
- [docker](https://www.docker.com/)
- [docker-compose](https://docs.docker.com/compose/) 

> Container's user is a non-root user.

Use the docker compose file available in this repository:

```bash
docker compose -f docker/compose.yaml up -d
```

This commands starts in detached mode the following containers:
- A fed-mgr-rally application.
- A fed-mgr REST API instance on port 8000 of your host.
- A MySQL DB with a dedicated volume for fed-mgr data.

Use the Federation Manager [Swagger UI](http://localhost:8000/api/v1/docs#/) to:
- POST/users/ : to create an user with their token 
- POST/providers : to create a provider with that user as site admin
- POST/regions : to add a region to that provider
- POST/project : to add a project to that provider

The variables are the same described in the section [Config variables](#config-variables).
Once the provider information has been saved into the Federation Manager DB, enter into the container:
```bash
docker exec -it fed-mgr-rally /bin/bash
```
and run the following command:
```
python src/main.py
```
This command will automatically launch Rally tests on the providers present in the Federation Manager's DB.

## Config variables

The variables `provider_name`, `auth_url`, `region`, `user`, `password`, `project` define the provider environment against which Rally tests will run.

The variable `flavor_name` defines the flavor of the VMs to test; its default value is tiny.

The variable `public_net` indicates the public network of the provider and the variable `floating_ips_enable` can be set to True to test floating IP association and dissociation on the specified public network; if False, floating IP operations are not tested. The default value of `public_net` is public.
If you want to test volume creation and attachment and you have more than one network, set `cinder_net_id` to the ID of the network that the volume should be connected to. That network must include a subnet so instances can boot. The default value of `cinder_net_id` is None.

## Environment variables

| Name | Type | Required | Default | Description |
|-|-|-|-|-|
| LOG_LEVEL | str | No | INFO | Logs level. One between: _CRITICAL_, _ERROR_, _WARNING_, _INFO_ or _DEBUG_ |
| SECRET_KEY | str | No | None | Secret key used to encrypt values in the DB. **To generate a valid key run the following command in shell and copy the generated output: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`** |
| KAFKA_ENABLE | bool | No | False | Enable kafka communication |
| KAFKA_BOOTSTRAP_SERVERS | str | No | localhost:9092 | Kafka server hostnames. DNS name and port. Can be a comma separeted list of DNS names |
| KAFKA_TOPIC | str | No | rally_results | Kafka topic with the results of the rally tests performed over the federated resource providers
| KAFKA_TOPIC_TIMEOUT | int | No | 1000 | Number of ms to wait when reading published messages |
| KAFKA_MAX_REQUEST_SIZE | int | No | 104857600 | Maximum size of a request to send to kafka (B)
| KAFKA_CLIENT_NAME | str | No | fedmgr | Client name to use when connecting to kafka |
| KAFKA_ALLOW_AUTO_CREATE_TOPICS | bool | No | False | Enable automatic creation of new topics if not yet in kafka |
| KAFKA_SSL_ENABLE | bool | No | False | Enable SSL connection with kafka |
| KAFKA_SSL_CACERT_PATH | str | No | None | Path to the SSL CA cert file. Mandatory if `KAFKA_SSL_ENABLE` is True |
| KAFKA_SSL_CERT_PATH | str | No | None | Path to the SSL cert file. Mandatory if `KAFKA_SSL_ENABLE` is True |
| KAFKA_SSL_KEY_PATH | str | No | None | Path to the SSL Key file. Mandatory if `KAFKA_SSL_ENABLE` is True |
| KAFKA_SSL_PASSWORD | str | No | None | SSL password for encrypted certs |
| KAFKA_MSG_VERSION | str | No | 1.0.0 | Message version for federation-tests-result topic |
| RALLY_ENVS_FOLDER | str | No | ./environments/ | Folder for provider environments |
| RALLY_ARGS_FOLDER | str | No | ./args/ | Folder for provider args |
| RALLY_REPORT_FOLDER | str | No | ./reports/ | Folder for provider test results |
| FED_MGR_API_URL | str | No | http://localhost:8000/api/v1/ | Rest API URL of the Federation Manager |
| X_API_KEY | str | No | None | API Key to access the Federation Manager API |
| API_SIZE | int | No | 5 | Number of items to retrieve per page when calling the Federation Manager API |
| API_PAGE | int | No | 1 | Page number to retrieve when calling the Federation Manager API |
| API_TIMEOUT | int | No | 15 | Timeout in seconds for Federation Manager API calls |
| REQUESTED_PROVIDER_STATUS | list[str] | No | ["evaluation", "pre_production", "active", "deprecated", "degraded", "maintenance", "re_evaluation"], | List of provider status codes allowed to run the tests |


## Developers

In this section there are a set of instructions for the developers of the application.

Requirements:
- python >= 3.12
- [poetry](https://python-poetry.org/) >= 2.1: needed to install, update and delete python packages.

Within the python libraries that will be installed in development mode there are some handful development tools
- [ruff](https://docs.astral.sh/ruff/): needed to check linting and code formatting.
- [pre-commit](https://pre-commit.com/): framework for managing and maintaining multi-language pre-commit hooks.

Prepare your environment as defined in [Local mode](#local-mode) section. **Since you are installing the dependencies in developmente mode, omit the `--without dev` section when installing the dependencies.**

**The first time you clone this project, after you have installed the python packages, run `pre-commit install` to install and enable the pre-commit hooks.**
