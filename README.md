# Canary-CD

Continuous Deployment API for Container and Static Pages

### Docs
- [Documentation](http://docs.rehborn.dev)
- [API](http://docs.rehborn.dev/api/)
- [CLI](http://docs.rehborn.dev/cli/)

## Development

### Run with uvicorn
```shell
echo "SALT=$(openssl rand -base64 32)" > .env
ROOT_KEY=test python -m uvicorn canary_cd.main:app --reload --port 8001 
```

### Linter
```shell
poetry run pylint canary_cd
```

### Tests
```shell
poetry run pytest tests/
```

### Coverage
```shell
poetry run coverage run --source canary_id -m pytest tests/ 
poetry run coverage report -m
```
