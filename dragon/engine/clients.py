# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# For more information please visit: https://wiki.openstack.org/wiki/TaskFlow

from oslo.config import cfg

from dragon.openstack.common import importutils
from dragon.openstack.common import log as logging

from dragon.common import dragon_keystoneclient as dkc
from dragon.common import exception

from novaclient import client as novaclient
from novaclient import shell as novashell
from glanceclient import client as glanceclient
from heatclient import client as heatclient

logger = logging.getLogger(__name__)

try:
    from swiftclient import client as swiftclient
except ImportError:
    swiftclient = None
    logger.info('swiftclient not available')
try:
    from neutronclient.v2_0 import client as neutronclient
except ImportError:
    neutronclient = None
    logger.info('neutronclient not available')
try:
    from cinderclient import client as cinderclient
except ImportError:
    cinderclient = None
    logger.info('cinderclient not available')

try:
    from ceilometerclient.v2 import client as ceilometerclient
except ImportError:
    ceilometerclient = None
    logger.info('ceilometerclient not available')


cloud_opts = [
    cfg.StrOpt('cloud_backend',
               default=None,
               help="Cloud module to use as a backend. Defaults to OpenStack.")
]

swiftbackup_service_opts = [
    cfg.StrOpt('backup_swift_tenant',
               default='demo',
               help='The tenant to use for swift'),
    cfg.StrOpt('backup_swift_url',
               default='http://9.148.45.13:5000/v2.0',
               help='The URL of the Swift endpoint'),
    cfg.StrOpt('backup_swift_auth',
               default='single_user',
               help='Swift authentication mechanism'),
    cfg.StrOpt('backup_swift_user',
               default='demo',
               help='Swift user name'),
    cfg.StrOpt('backup_swift_key',
               default='aab93a50cbb142d0',
               help='Swift key for authentication'),
    cfg.StrOpt('backup_swift_container',
               default='volumebackups',
               help='The default Swift container to use'),
    cfg.IntOpt('backup_swift_object_size',
               default=52428800,
               help='The size in bytes of Swift backup objects'),
    cfg.IntOpt('backup_swift_retry_attempts',
               default=3,
               help='The number of retries to make for Swift operations'),
    cfg.IntOpt('backup_swift_retry_backoff',
               default=2,
               help='The backoff time in seconds between Swift retries'),
    cfg.StrOpt('backup_compression_algorithm',
               default='zlib',
               help='Compression algorithm (None to disable)'),
]


cfg.CONF.register_opts(cloud_opts)
cfg.CONF.register_opts(swiftbackup_service_opts)


class OpenStackClients(object):
    '''
    Convenience class to create and cache client instances.
    '''

    def __init__(self, context):
        self.context = context
        self._nova = {}
        self._keystone = None
        self._swift = None
        self._neutron = None
        self._remote_neutron = None
        self._remote_nova = None
        self._cinder = None
        self._ceilometer = None
        self._glance = None
        self._heat = None
        self._glanceImageService = None

    @property
    def auth_token(self):
        # if there is no auth token in the context
        # attempt to get one using the context username and password
        return self.context.auth_token or self.keystone().auth_token

    def keystone(self):
        if self._keystone:
            return self._keystone

        self._keystone = dkc.KeystoneClient(self.context)
        return self._keystone

    def heat(self):
        def format_parameters(params):
            parameters = {}
            for count, p in enumerate(params, 1):
                parameters['Parameters.member.%d.ParameterKey' % count] = p
                parameters['Parameters.member.%d.ParameterValue' % count] =\
                    params[p]
            return parameters

        if self._heat:
            return self._heat

        con = self.context
        api_version = "1"
# insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
# cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
        endpoint = self.url_for(service_type='orchestration')
        logger.info('heatclient connection created using token'
                    ' %s and url %s' % (con.username, endpoint))

        kwargs = {
            'token': self.auth_token,
            'insecure': False,
            'ca_file': None,
            'username': con.username
        }

        self._heat = heatclient.Client(api_version, endpoint, **kwargs)
        self._heat.format_parameters = format_parameters
        return self._heat

    def glance(self):
        if self._glance:
            return self._glance

        con = self.context
        args = {
            'auth_version': '2.0',
            'tenant_name': con.tenant,
            'username': con.username,
            'key': None,
            'auth_url': None,
            'token': self.auth_token,
            'endpoint': self.url_for(service_type='image')
        }
        self._glance = glanceclient.Client(1, **args)
        return self._glance

    def url_for(self, **kwargs):
        return self.keystone().url_for(**kwargs)

    def nova(self, service_type='compute'):
        if service_type in self._nova:
            return self._nova[service_type]

        con = self.context
        if self.auth_token is None:
            logger.error("Nova connection failed, no auth_token!")
            return None

        computeshell = novashell.OpenStackComputeShell()
        extensions = computeshell._discover_extensions("1.1")

        args = {
            'project_id': con.tenant,
            'auth_url': con.auth_url,
            'service_type': service_type,
            'username': None,
            'api_key': None,
            'extensions': extensions
        }

        client = novaclient.Client(1.1, **args)

        management_url = self.url_for(service_type=service_type)
        client.client.auth_token = self.auth_token
        client.client.management_url = management_url

        self._nova[service_type] = client
        return client

    def remote_nova(self, service_type='compute'):
        if novaclient is None:
            return None
        if self._remote_nova:
            return self._remote_nova

        if self.auth_token is None:
            logger.error("Nova connection failed, no auth_token!")
            return None

        try:
            self._remote_nova =\
                novaclient.Client(1.1,
                                  cfg.CONF['draas_username'],
                                  cfg.CONF['draas_password'],
                                  project_id=cfg.CONF['draas_tenant_name'],
                                  auth_url=cfg.CONF['draas_keystone_url'])

        except Exception, e:
            logger.error("Failed getting remote nova connection %s" % (e))
            return None

        return self._remote_nova

    def swift(self):
        if swiftclient is None:
            return None
        if self._swift:
            return self._swift

        if self.auth_token is None:
            logger.error("Swift connection failed, no auth_token!")
            return None

        if cfg.CONF['backup_swift_auth'] == 'single_user':
            if cfg.CONF['backup_swift_user'] is None:
                logger.error(_("single_user auth mode enabled, "
                               "but %(param)s not set")
                             % {'param': 'backup_swift_user'})
                raise exception.UserParameterMissing(key='backup_swift_user')
            logger.warning('Swift connection created using user %s '
                           'and url %s'
                           % (cfg.CONF['backup_swift_user'],
                              cfg.CONF['backup_swift_url']))

            tenant = cfg.CONF['backup_swift_tenant']
            user = cfg.CONF['backup_swift_user']
            key = cfg.CONF['backup_swift_key']
            authurl = cfg.CONF['backup_swift_url']

            self._swift = swiftclient.Connection(
                authurl=cfg.CONF['backup_swift_url'],
                auth_version='2.0',
                tenant_name=cfg.CONF['backup_swift_tenant'],
                user=cfg.CONF['backup_swift_user'],
                key=cfg.CONF['backup_swift_key'],
                retries=3,
                starting_backoff=2)
        else:
            con = self.context
            tenant = con.tenant
            user = con.username
            key = None
            authurl = None

            args = {
                'auth_version': '2.0',
                'tenant_name': tenant,
                'user': user,
                'key': key,
                'authurl': authurl,
                'preauthtoken': self.auth_token,
                'preauthurl': self.url_for(service_type='object-store'),
                'retries': 3,
                'starting_backoff': 2
            }
            self._swift = swiftclient.Connection(**args)
        return self._swift

    def neutron(self):
        if neutronclient is None:
            return None
        if self._neutron:
            return self._neutron

        con = self.context
        if self.auth_token is None:
            logger.error("Neutron connection failed, no auth_token!")
            return None

        args = {
            'auth_url': con.auth_url,
            'service_type': 'network',
            'token': self.auth_token,
            'endpoint_url': self.url_for(service_type='network')
        }

        self._neutron = neutronclient.Client(**args)

        return self._neutron

    def remote_neutron(self):
        if neutronclient is None:
            return None
        if self._remote_neutron:
            return self._remote_neutron

        if self.auth_token is None:
            logger.error("Neutron connection failed, no auth_token!")
            return None

        self._remote_neutron =\
            neutronclient.Client(username=cfg.CONF['backup_swift_user'],
                                 password=cfg.CONF['backup_swift_key'],
                                 tenant_name=cfg.CONF['backup_swift_tenant'],
                                 auth_url=cfg.CONF['backup_swift_url'])

        return self._remote_neutron

    def cinder(self):
        if cinderclient is None:
            return self.nova('volume')
        if self._cinder:
            return self._cinder

        con = self.context
        if self.auth_token is None:
            logger.error("Cinder connection failed, no auth_token!")
            return None

        args = {
            'auth_url': con.auth_url,
            'project_id': con.tenant,
            'tenant_id': con.tenant,
            'username': con.username,
            'api_key': None
        }

        self._cinder = cinderclient.Client('2', **args)
        management_url = self.url_for(service_type='volumev2')
        self._cinder.client.auth_token = self.auth_token
        self._cinder.client.management_url = management_url

        return self._cinder

    def ceilometer(self):
        if ceilometerclient is None:
            return None
        if self._ceilometer:
            return self._ceilometer

        if self.auth_token is None:
            logger.error("Ceilometer connection failed, no auth_token!")
            return None
        con = self.context
        args = {
            'auth_url': con.auth_url,
            'service_type': 'metering',
            'project_id': con.tenant,
            'token': lambda: self.auth_token,
            'endpoint': self.url_for(service_type='metering'),
        }

        client = ceilometerclient.Client(**args)

        self._ceilometer = client
        return self._ceilometer


if cfg.CONF.cloud_backend:
    cloud_backend_module = importutils.import_module(cfg.CONF.cloud_backend)
    Clients = cloud_backend_module.Clients
else:
    Clients = OpenStackClients

logger.debug('Using backend %s' % Clients)
