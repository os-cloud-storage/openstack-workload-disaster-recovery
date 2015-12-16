# vim: tabstop=4 shiftwidth=4 softtabstop=4

'''-------------------------------------------------------------------------
Copyright IBM Corp. 2015, 2015 All Rights Reserved
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
Limitations under the License.
-------------------------------------------------------------------------'''

from django.conf import settings # noqa
from dragonclient import client as dragon_client
from openstack_dashboard.api import base
import logging


LOG = logging.getLogger(__name__)


def format_parameters(params):
    parameters = {}
    for count, p in enumerate(params, 1):
        parameters['Parameters.member.%d.ParameterKey' % count] = p
        parameters['Parameters.member.%d.ParameterValue' % count] = params[p]
    return parameters


def dragonclient(request, password=None):
    api_version = "1"
    insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
    cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
    endpoint = base.url_for(request, 'dr')
    LOG.debug('dragonclient connection created using token "%s" and url "%s"' %
              (request.user.token.id, endpoint))
    kwargs = {
        'token': request.user.token.id,
        'insecure': insecure,
        'ca_file': cacert,
        'project': request.user.tenant_id,
        'username': request.user.username,
        'password': password
        #'timeout': args.timeout,
        #'ca_file': args.ca_file,
        #'cert_file': args.cert_file,
        #'key_file': args.key_file,
    }
    client = dragon_client.Client(api_version, endpoint, **kwargs)
    LOG.debug("dragonclient obtained %s" % type(client))
    LOG.debug("dragonclient dir: %s" % dir(client))
    client.format_parameters = format_parameters
    return client

