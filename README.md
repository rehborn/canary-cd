<div align="center">

[![CanaryCD](https://docs.rehborn.dev/assets/canary-cd.png)](http://docs.rehborn.dev)

**Continuous Deployment API for Container and Static Pages**

[Source](https://github.com/rehborn/canary-cd) &middot; [Documentation](http://docs.rehborn.dev) 

[![PyPI-Badge]](https://pypi.org/project/canary-cd/)
![Python-Badge]
[![License-Badge]](https://github.com/rehborn/canary-cd/blob/main/LICENSE)

[PyPI-Badge]:
https://img.shields.io/pypi/v/canary-cd?style=flat-square&color=306998&label=PyPI&labelColor=FFD43B
[Python-Badge]:
https://img.shields.io/pypi/pyversions/canary-cd?style=flat-square&color=306998&label=Python
[License-Badge]:
https://img.shields.io/github/license/rehborn/canary-cd?style=flat-square&label=License
</div>

## Documentation
- [Setup](http://docs.rehborn.dev/setup/)
- [CLI](http://docs.rehborn.dev/cli/)
- [API](http://docs.rehborn.dev/api/) 

## Development

### Run with uvicorn
```shell
echo "SALT=$(openssl rand -base64 32)" > .env
ROOT_KEY=test python -m uvicorn canary_cd.main:app --reload --port 8001 
```

### Linter
```shell
uv run pylint canary_cd
```

### Tests
```shell
uv run pytest tests/
```

### Coverage
```shell
uv run coverage run --source canary_cd -m pytest tests/
uv run coverage report -m --skip-covered
```

### Docker

#### test standalone
```shell
docker compose build
docker compose up
```

#### test with traefik
```shell
docker compose -f compose.traefik.yml  up
```