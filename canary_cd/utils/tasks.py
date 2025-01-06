import json
import os
import re
import shutil
import tarfile
import tempfile
import uuid
import yaml
from asyncio.subprocess import create_subprocess_shell, PIPE
from pathlib import Path
from time import time, strftime

import git
import docker

from canary_cd.database import *
from canary_cd.dependencies import ch
from canary_cd.settings import logger, REPO_CACHE, PAGES_CACHE, STATIC_BACKEND_NAME, DYN_CONFIG_CACHE
from canary_cd.utils.notify import discord_webhook

REMOTE_RE = r'^(?:(https?|git|git\+ssh|ssh):\/\/)?(?:([^@\/:]+)(?::([^@\/:]+))?@)?([^:\/]+)(?::(\d+))?(?:[\/:](.+?))(?:\.git)?$'


async def _run_cmd(cmd: str, env=None) -> tuple[str, str]:
    if env is None:
        env = {}
    proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE, env={**os.environ, **env})
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode()


async def generate_ssh_keypair(name: str, ssh_key_type='ed25519') -> [str, str]:
    logger.debug(f"Generating SSH keypair {name}")
    temp_dir = tempfile.TemporaryDirectory(delete=True)
    key_path = Path(temp_dir.name, name)
    pub_path = f'{key_path}.pub'
    param = f'ssh-keygen -t {ssh_key_type} -C "{name}" -N "" -f {key_path}'
    stdout, stderr = await _run_cmd(param)
    private_key = open(key_path, 'r', encoding='utf-8').read()
    public_key = open(pub_path, 'r', encoding='utf-8').read().rstrip('\n')

    return private_key, public_key


async def generate_ssh_pubkey(private_key: str) -> str:
    logger.debug(f"Generating SSH Public Key")
    temp_dir = tempfile.TemporaryDirectory(delete=True)
    key_path = Path(temp_dir.name, 'temp_key')

    def opener(p, f):
        return os.open(p, f, 0o600)

    open(key_path, 'w', encoding='utf-8', opener=opener).write(private_key)
    param = f'ssh-keygen -f {key_path} -y'
    stdout, stderr = await _run_cmd(param)
    return stdout.rstrip('\n')


async def git_pull(repo_path: Path, remote: str, branch: str, auth_type: str or None, auth_key: str or None) -> bool:
    """
    Git Pull Repository

    - change or create directory
    - add remote
    - fetch origin
    - switch branch
    - pull changes
    """
    # https://x-access-token:{app_access_token}@github.com/foo/bar
    # https://{personal_access_token}@github.com/foo/bar
    # https://{user}@github.com/foo/bar
    # git@github.com:foo/bar

    logger.debug(f'Git Clone {auth_type} {remote}')
    temp_dir = None

    if not repo_path.exists():
        os.makedirs(repo_path, exist_ok=True)

    repo = git.Repo.init(repo_path)

    # remove stale origins
    try:
        repo.delete_remote(repo.remote())
    except ValueError:
        pass

    # dissect remote uri
    remote_match = re.match(REMOTE_RE, remote)
    try:
        protocol, user, passwd, host, port, path = remote_match.groups()
    except AttributeError:
        logger.error(f"Aborting Cloning: can't parse remote: {remote}")
        return False

    port = f':{port}' if port else ''  # optional port

    # disable interactive prompting
    repo.git.update_environment(GIT_TERMINAL_PROMPT='0')

    # SSH Key Authentication
    if auth_type == 'ssh':
        remote = f'{user}@{host}{port}:{path}'
        repo.create_remote('origin', remote)

        temp_dir = tempfile.TemporaryDirectory()
        key_path = Path(temp_dir.name, 'keyfile')

        def opener(p, f):
            return os.open(p, f, 0o600)

        open(key_path, 'w', encoding='utf-8', opener=opener).write(auth_key)

        git_ssh_command = f'ssh -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -F /dev/null -i {key_path}'
        repo.git.update_environment(GIT_SSH_COMMAND=git_ssh_command)

    # GitHub PAT Authentication
    elif auth_type == 'pat':
        protocol = protocol if protocol else 'https'
        user = user if user and not user == 'git' else path.split('/')[0]  # guess user based on path
        remote = f'{protocol}://{user}:{auth_key}@{host}{port}/{path}'
        repo.create_remote('origin', remote)
    else:
        repo.create_remote('origin', remote)

    # if not repo.remotes:
    #     logger.error(f'No remotes found for {auth_type} {remote}')
    #     return False

    try:
        repo.remotes.origin.pull(branch)
        successful_cloned = True
    except git.exc.GitCommandError as e:
        logger.error(f'git clone error: {e.stderr}')
        successful_cloned = False

    repo.delete_remote(repo.remote())
    if temp_dir:
        temp_dir.cleanup()

    return successful_cloned


async def service_deploy(env: str, repo_path: Path, variables: dict) -> str:
    os.chdir(repo_path)
    repo_files_root = os.listdir(repo_path)

    manifests = []
    for filename in repo_files_root:
        name, ext = os.path.splitext(filename)
        if ext in ['.yaml', '.yml']:
            if name in ['docker-compose', 'compose']:
                logger.debug(f"Found: {name}")
                manifests.append(filename)
            elif name in [f'docker-compose.{env}', f'compose.{env}']:
                logger.debug(f"Found: {name}")
                manifests.append(filename)

    if manifests:
        params = ' -f '.join(manifests)
        logger.debug(f"Manifest Params: {params}")

        # docker
        stdout, stderr = await _run_cmd(f'docker compose -f {params} up -d --force-recreate', env=variables)

        # docker_ps_format = 'json'
        docker_ps_format = '"{{.Names}} {{.Image}} {{.Status}}"'
        stdout_, stderr_ = await _run_cmd(f'docker compose ps --format {docker_ps_format}', env=variables)

        stdout_logs, stderr_logs = await _run_cmd('docker compose logs --tail=25', env=variables)

        out = ""
        for output in [stdout, stderr, stdout_, stderr_, stdout_logs, stderr_logs]:
            if len(output) > 0:
                out += f"{output}\n"
    else:
        logger.error('No manifest found')
        out = 'No manifest found, nothing deployed'

    return out


async def deploy_init(db: Database, environment_id: uuid.UUID):
    q = select(Environment).where(Environment.id == environment_id)
    env = db.exec(q).one()
    logger.info(f"[{env.project.name}] Deployment initialized for environment {env.name}")

    # get webhook url
    webhook = db.exec(select(Config).where(Config.key == 'DISCORD_WEBHOOK')).first()
    webhook_url = webhook.value if webhook else None
    if webhook_url:
        message = f"### :arrow_forward: {env.project.name}:{env.name}@{env.branch} Deployment started"
        discord_webhook(webhook_url, message)

    # decrypt environment variables
    logger.debug(f"[{env.project.name}] Decrypting {len(env.variables)} Variables for Environment {env.name} ")
    variables = {}
    for var in env.variables:
        variables[var.key] = ch.decrypt(json.loads(var.value))

    out = '-'
    if env.project.remote:
        logger.debug(f"[{env.project.name}] Pulling Repository {env.project.remote}@{env.branch}")
        repo_path = REPO_CACHE / env.project.name / f"{env.name}-{env.branch}"
        auth_key = None
        auth_type = None

        if env.project.git_key:
            auth_key = ch.decrypt(env.project.git_key.nonce, env.project.git_key.ciphertext)
            auth_type = env.project.git_key.auth_type

        options = {
            'repo_path': repo_path,
            'remote': env.project.remote,
            'branch': env.branch,
            'auth_type': auth_type,
            'auth_key': auth_key,
        }

        clone_successful = await git_pull(**options)

        # run deployment
        if clone_successful:
            logger.info(f"[{env.project.name}] Deploying {repo_path}")
            out = await service_deploy(env.name, repo_path, variables)
            logger.debug(out)
        else:
            message = f"[{env.project.name}] Cloning not successful, please check logs"
            logger.error(message)
    else:
        message = f"[{env.project.name}] No Remote Found"
        logger.error(message)

    # send notification
    if webhook_url:
        logger.debug(f"[{env.project.name}] Sending Notifications")
        messages = [
            f"### :information_source: {env.project.name}:{env.name}@{env.branch} Status\n```{out[:2000]}```\n"
            f"### :white_check_mark: {env.project.name}:{env.name}@{env.branch} Deployed"
        ]
        for message in messages:
            discord_webhook(webhook_url, message)


async def deploy_status(repo_path: Path):
    try:
        os.chdir(repo_path)
    except FileNotFoundError:
        logger.error(f"[{repo_path.name}] does not exist, cannot fetch status")
        return {'detail', f"[{repo_path.name}] does not exist, cannot fetch status"}

    results = {}

    param = 'docker compose ps --format json'
    stdout, stderr = await _run_cmd(param)
    ps = json.loads(stdout)
    if type(ps) == dict:
        ps = [ps]
    results['ps'] = ps

    param = 'docker compose logs --tail=25'
    stdout, stderr = await _run_cmd(param)
    results['logs'] = stdout

    return results


async def extract_page(fqdn, temp_dir, job_id=None):
    logger.debug(f"Page {job_id}: extracting")
    content = tarfile.open(Path(temp_dir.name, 'stream-upload'))
    content.extractall(PAGES_CACHE / f'{fqdn}-temp')

    dist_dir = "."
    for _dist_dir in os.listdir(PAGES_CACHE / f'{fqdn}-temp'):
        if _dist_dir in ['public', 'dist', 'site', 'docs']:
            dist_dir = _dist_dir
            continue
    logger.debug(f"Page {job_id}: dist_dir: {dist_dir}")

    logger.debug(f"Page {job_id}: deploying")
    # shutil.move(PAGES_CACHE / fqdn, Path(PAGES_CACHE / f'{fqdn}-{strftime('%Y-%m-%d_%H-%M-%S')}'))
    shutil.rmtree(PAGES_CACHE / fqdn)
    shutil.move(Path(PAGES_CACHE / f'{fqdn}-temp/{dist_dir}'), PAGES_CACHE / fqdn)

    logger.debug(f"Page {job_id}: cleanup temporary files")
    temp_dir.cleanup()


async def page_traefik_config(fqdn: str):
    config = {
        'http': {
            'routers': {
                f'backend-router-{fqdn}': {
                    'service': f'backend-service-{fqdn}',
                    'rule': f'Host(`{fqdn}`)',
                    'entryPoints': 'tls',
                    'tls': {
                        'certResolver': 'letsencrypt'
                    }

                }
            },
            'services': {
                f'backend-service-{fqdn}': {
                    'loadBalancer': {
                        'passHostHeader': True,
                        'servers': [{
                            'url': STATIC_BACKEND_NAME,
                        }]
                    }
                }
            }
        }
    }
    with open(DYN_CONFIG_CACHE / f'{fqdn}.yml', 'w') as dump:
        yaml.dump(config, dump)


async def redirect_traefik_config(source: str, destination: str):
    config = {
        'http': {
            'routers': {
                f'forward-router-{source}': {
                    'service': 'noop@internal',
                    'rule': f'Host(`{source}`)',
                    'entryPoints': 'tls',
                    'tls': {
                        'certResolver': 'letsencrypt'
                    },
                    'middlewares': [f'forward-middleware-{source}'],
                    'priority': 1,
                }
            },
            'middlewares': {
                f'forward-middleware-{source}': {
                    'redirectRegex': {
                        'regex': f'^https://{source}/(.*)',
                        'replacement': f'https://{destination}/${1}',
                        'permanent': True,
                    }
                }
            }
        }
    }
    with open(DYN_CONFIG_CACHE / f'{source}.yml', 'w') as dump:
        yaml.dump(config, dump)
