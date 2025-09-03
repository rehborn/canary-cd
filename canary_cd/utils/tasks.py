import json
import re
import shutil
import tarfile
import tempfile
import yaml
from asyncio import subprocess
from pathlib import Path

import git

from canary_cd.database import *
from canary_cd.dependencies import ch
from canary_cd.settings import logger, REPO_CACHE, PAGES_CACHE, DYN_CONFIG_CACHE, HTTPD, HTTPD_CONFIG_DUMP
from canary_cd.utils.notify import discord_webhook
from canary_cd.utils.httpd_conf import TraefikConfig

REMOTE_RE = r'^(?:(https?|git|git\+ssh|ssh):\/\/)?(?:([^@\/:]+)(?::([^@\/:]+))?@)?([^:\/]+)(?::(\d+))?(?:[\/:](.+?))(?:\.git)?$'


async def _run_cmd(cmd: str, env=None) -> tuple[str, str]:
    if env is None:
        env = {}
    proc = await subprocess.create_subprocess_shell(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, **env})
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

        temp_dir = tempfile.TemporaryDirectory()
        key_path = Path(temp_dir.name, 'keyfile')

        def opener(p, f):
            return os.open(p, f, 0o400)

        open(key_path, 'w', encoding='utf-8', opener=opener).write(auth_key)

        git_ssh_command = f'ssh -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -F /dev/null -i {key_path}'
        repo.git.update_environment(GIT_SSH_COMMAND=git_ssh_command)

    # GitHub PAT Authentication
    elif auth_type == 'pat':
        protocol = protocol if protocol else 'https'
        user = user if user and not user == 'git' else path.split('/')[0]  # guess user based on path
        remote = f'{protocol}://{user}:{auth_key}@{host}{port}/{path}'

    repo.create_remote('origin', remote)

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


def find_manifests(repo_path: Path, branch=None) -> list:
    manifests = []
    for filename in os.listdir(repo_path):
        name, ext = os.path.splitext(filename)
        if ext in ['.yaml', '.yml']:
            if name in ['docker-compose', 'compose']:
                logger.debug(f"Found: {name}")
                manifests.append(filename)
            if branch and name in [f'docker-compose.{branch}', f'compose.{branch}']:
                logger.debug(f"Found: {name}")
                manifests.append(filename)
    return manifests


async def service_deploy(repo_path: Path, variables: dict, branch=None) -> str:
    os.chdir(repo_path)
    manifests = find_manifests(repo_path, branch)

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


async def deploy_init(db: Database, project_id: uuid.UUID):
    q = select(Project).where(Project.id == project_id)
    project = db.exec(q).one()
    logger.info(f"[{project.name}] Deployment initialized")

    # get webhook url
    webhook = db.exec(select(Config).where(Config.key == 'DISCORD_WEBHOOK')).first()
    webhook_url = webhook.value if webhook else None
    if webhook_url:
        message = f"### :arrow_forward: [{project.name}] @{project.branch} Deployment started"
        discord_webhook(webhook_url, message)

    # decrypt environment variables
    logger.debug(f"[{project.name}] Decrypting {len(project.secrets)} Variables for Environment {project.name} ")
    variables = {}
    for var in project.secrets:
        variables[var.key] = ch.decrypt(json.loads(var.value))

    out = '-'
    if project.remote:
        logger.debug(f"[{project.name}] Pulling Repository {project.remote}@{project.branch}")
        repo_path = REPO_CACHE / project.name
        auth_key = None
        auth_type = None

        if project.auth:
            auth_key = ch.decrypt(project.auth.nonce, project.auth.ciphertext)
            auth_type = project.auth.auth_type

        options = {
            'repo_path': repo_path,
            'remote': project.remote,
            'branch': project.branch,
            'auth_type': auth_type,
            'auth_key': auth_key,
        }

        clone_successful = await git_pull(**options)

        # run deployment
        if clone_successful:
            logger.info(f"[{project.name}] Deploying {repo_path}")
            out = await service_deploy(repo_path, variables, project.branch)
            logger.debug(out)
        else:
            message = f"[{project.name}] Cloning not successful, please check logs"
            logger.error(message)
    else:
        message = f"[{project.name}] No Remote Found"
        logger.error(message)

    # send notification
    if webhook_url:
        logger.debug(f"[{project.name}] Sending Notifications")
        messages = [
            f"### :information_source: {project.name}:{project.remote}@{project.branch} Status\n```{out[:2000]}```\n"
            f"### :white_check_mark: {project.name}:{project.remote}@{project.branch} Deployed"
        ]
        for message in messages:
            discord_webhook(webhook_url, message)


async def deploy_stop(repo_path: Path):
    try:
        os.chdir(repo_path)
    except FileNotFoundError:
        logger.error(f"[{repo_path.name}] does not exist, cannot fetch status")
        return

    param = 'docker compose down'
    stdout, stderr = await _run_cmd(param)
    return {'logs': stdout}


async def deploy_status(repo_path: Path, branch=None):
    try:
        os.chdir(repo_path)
    except FileNotFoundError:
        logger.error(f"[{repo_path.name}] does not exist, cannot fetch status")
        return {'detail': 'repo_path not found'}

    manifests = find_manifests(repo_path, branch)
    if manifests:
        params = ' -f '.join(manifests)
    else:
        logger.error(f"[{repo_path}] no manifests found")
        return {'detail': 'no manifests found'}

    results = {}
    param = f'docker compose -f {params} ps --format json'
    stdout, stderr = await _run_cmd(param)
    if stdout:
        ps = json.loads(stdout)
        if type(ps) == dict:
            ps = [ps]
        results['ps'] = ps

    param = 'docker compose logs --tail=25'
    stdout, stderr = await _run_cmd(param)
    if stdout:
        results['logs'] = stdout

    return results


async def extract_page(fqdn, temp_dir, job_id=None):
    logger.debug(f"Page {job_id}: extracting")
    content = tarfile.open(Path(temp_dir.name, 'stream-upload'))
    content.extractall(PAGES_CACHE / f'{fqdn}-temp', filter='data')

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


async def page_init(fqdn: str, cors_hosts: str):
    os.makedirs(PAGES_CACHE / fqdn, exist_ok=True)
    open(PAGES_CACHE / fqdn / 'index.html', 'w').write('<h1>PONG</h1>')
    open(PAGES_CACHE / fqdn / '404.html', 'w').write('<h1>404</h1>')

    if HTTPD_CONFIG_DUMP and HTTPD == 'traefik':
        tc = TraefikConfig()
        tc.add_page(fqdn, cors_hosts)
        with open(DYN_CONFIG_CACHE / f'{fqdn}.yml', 'w') as dump:
            yaml.dump(tc.render(), dump)


async def redirect_init(source: str, destination: str):
    if HTTPD_CONFIG_DUMP and HTTPD == 'traefik':
        tc = TraefikConfig()
        tc.add_redirect(source, destination)
        with open(DYN_CONFIG_CACHE / f'{source}.yml', 'w') as dump:
            yaml.dump(tc.render(), dump)
