CONFIG_KEYS = [
    'ROOT_KEY',

    # not implemented
    # Notification Config
    'SLACK_WEBHOOK',
    'DISCORD_WEBHOOK',

    # GitHub App Config
    'GITHUB_APP_ID',
    'GITHUB_SECRET_FILE',
    'GITHUB_WEBHOOK_SECRET',
]

AUTH_TYPES = [
    "ssh",
    "pat",
    "token"
]

FQDN_PATTERN = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"
FQDN_EXAMPLES = ['example.com', 'www.example.com']

# NAME_PATTERN = r"^([\w]{1})[\w\d-]+$"
NAME_PATTERN = r"^[\w-]+$"
NAME_EXAMPLES = ['example-name']

GIT_REPO_PATTERN = r"""
    ^
    (?:(?P<protocol>[https?|git|ssh]+:\/\/))?
    (?:(?P<login_user>[\w\d]+)@)?
    (?P<host>[\w\d.-]+)([:\/])
    (?P<user>[\w\d-]+)
    (?:(?P<namespace>\/[\w\d-]+))?
    /
    (?P<repo>[\w\d-]+)
    (?:\.git)? 
    (?:@(?P<branch>[\w.\-/]+))?
    $
"""

REPO_EXAMPLES = [
    "git@github.com:user/repo.git",
    "https://github.com/user/repo.git",

    "git@gitlab.com:user/namespace/repo.git",
    "https://gitlab.com/user/namespace/repo.git",

    "ssh://git@example.com:2222/user/repo.git",
]

AUTH_KEY_PATTERN = r".*"
AUTH_KEY_EXAMPLES = ["ssh-private-key", "ghp_1234"]
PUBLIC_KEY_EXAMPLES = ['ssh-ed25519 AAAAC..lGM key']

GITHUB_REPO_PATTERN = r"""
    ^
    (?P<user>[\w\d-]+)
    /
    (?P<repo>[\w\d-]+)
    (?:@(?P<branch>[\w.\-/]+))?
    $
"""

GITHUB_REPO_EXAMPLES = [
    "user/repo",
    "user/repo@branch",
    "user-name/repo-name@feature",
    "user-name/repo-name@feature-branch-1.0"
]


def single_pattern(pattern: str) -> str:
    return ''.join(pattern.split())
