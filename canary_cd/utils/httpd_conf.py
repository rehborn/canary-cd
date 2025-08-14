from canary_cd.settings import STATIC_BACKEND_NAME


class TraefikConfig:
    def __init__(self, default_service=False):
        self.routers = {}
        self.services = {}
        self.middlewares = {}

        if default_service:
            self.services[f'backend-service-static-pages'] = {
                'loadBalancer': {
                    'passHostHeader': True,
                    'servers': [{
                        'url': STATIC_BACKEND_NAME,
                    }]
                }
            }

    def add_page(self, fqdn: str, cors_hosts: str = None, add_service=True):
        self.routers[f'backend-router-{fqdn}'] = {
            'service': 'backend-service-static-pages',
            'rule': f'Host(`{fqdn}`)',
            'entryPoints': 'tls',
            'tls': {
                'certResolver': 'letsencrypt'
            }
        }

        if add_service:
            self.routers[f'backend-router-{fqdn}']['service'] = f'backend-service-{fqdn}'
            self.services[f'backend-service-{fqdn}'] = {
                'loadBalancer': {
                    'passHostHeader': True,
                    'servers': [{
                        'url': STATIC_BACKEND_NAME,
                    }]
                }
            }

        if cors_hosts:
            cors_hosts = cors_hosts.split(',') if cors_hosts else []
            cors_hosts = [host if host.startswith('http') else f'https://{host}' for host in cors_hosts]
            self.routers[f'backend-router-{fqdn}']['middlewares'] = [f'cors-middleware-{fqdn}']
            self.middlewares = {
                f'cors-middleware-{fqdn}': {
                    'headers': {
                        'accessControlAllowMethods': ['GET', 'OPTIONS', 'PUT'],
                        'accessControlAllowHeaders': '*',
                        'accessControlAllowOriginList': cors_hosts,
                        'accessControlMaxAge': 100,
                        'addVaryHeader': True,
                    }
                }
            }

    def add_redirect(self, source: str, destination: str):
        self.routers[f'forward-router-{source}'] = {
            'service': 'noop@internal',
            'rule': f'Host(`{source}`)',
            'entryPoints': 'tls',
            'tls': {
                'certResolver': 'letsencrypt'
            },
            'middlewares': [f'forward-middleware-{source}'],
            'priority': 1,
        }
        self.middlewares[f'forward-middleware-{source}'] = {
            'redirectRegex': {
                'regex': f'^https://{source}/(.*)',
                'replacement': f'https://{destination}/${1}',
                'permanent': True,
            }
        }


    def render(self):
        config = {'http': {}}
        if self.routers:
            config['http']['routers'] = self.routers

        for section in ['routers', 'services', 'middlewares']:
            if getattr(self, section):
                config['http'][section] = getattr(self, section)

        return config
