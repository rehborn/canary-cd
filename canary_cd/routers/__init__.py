from canary_cd.routers import config, auth, project, secret, page, redirect, deploy, webhook

routers = [
    config.router,
    auth.router,
    project.router,
    secret.router,
    page.router,
    redirect.router,
    deploy.router,
    webhook.router,
]
