# federation-manager-rally

Currently poetry project needs python >=3.13.
Install poetry and run `script.py` with the parameters regarding the new provider:
```
curl -sSL https://install.python-poetry.org | python3 -
poetry install --no-root
poetry run python script.py 
--auth-url https://test /
--region RegionOne /
--user username /
--password pwd /
--project ops /
--flavor_name small /
--public-net net /
--floating_ips_enable False /
--cinder_net_id 123
```
`flavor_name` default value is tiny, `public-net` default valiue is public, `cinder_net_id` default value is None.



