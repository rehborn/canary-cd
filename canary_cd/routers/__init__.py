from canary_cd.routers import config, git_key, project, env, page, redirect, deploy

routers = [
    git_key.router,
    project.router,
    env.router,
    page.router,
    redirect.router,
    deploy.router,
    config.router,
]
