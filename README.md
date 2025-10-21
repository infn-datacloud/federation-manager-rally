# federation-manager-rally

Currently poetry project needs python >=3.13.
Install poetry:
```
curl -sSL https://install.python-poetry.org | python3 -
poetry install --no-root
```
Create a new `src/.env` file, following the `src/.env.example` file.
Run `script.py` with the parameters regarding the new provider:
```
cd src
poetry run python script.py 
--provider_name my_name /
--provider_type openstack /
--auth_url https://my_url /
--region RegionOne /
--user my_username /
--password my_pwd /
--project my_ops /
--flavor_name small /
--public_net my_net /
--floating_ips_enable False /
--cinder_net_id my_net_id
```
The variables `provider_name`, `auth_url`, `region`, `user`, `password`, `project` define the provider environment against which Rally tests will run.

The variable `flavor_name` defines the flavor of the VMs to test; its default value is tiny.

The variable `public_net` indicates the public network of the provider and the variable `floating_ips_enable` can be set to True to test floating IP association and dissociation on the specified public network; if False, floating IP operations are not tested. The default value of `public_net` is public.
If you want to test volume creation and attachment and you have more than one network, set `cinder_net_id` to the ID of the network that the volume should be connected to. That network must include a subnet so instances can boot. The default value of `cinder_net_id` is None.



