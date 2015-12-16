# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from dragon.rpc import api
from dragon.openstack.common import log as logging

logger = logging.getLogger(__name__)


def extract_args(params):
    '''
    Extract any arguments passed as parameters through the API and return them
    as a dictionary. This allows us to filter the passed args and do type
    conversion where appropriate
    '''
    kwargs = {}
    try:
        timeout_mins = int(params.get(api.PARAM_TIMEOUT, 0))
    except (ValueError, TypeError):
        logger.exception('create timeout conversion')
    else:
        if timeout_mins > 0:
            kwargs[api.PARAM_TIMEOUT] = timeout_mins

    if api.PARAM_DISABLE_ROLLBACK in params:
        disable_rollback = params.get(api.PARAM_DISABLE_ROLLBACK)
        if str(disable_rollback).lower() == 'true':
            kwargs[api.PARAM_DISABLE_ROLLBACK] = True
        elif str(disable_rollback).lower() == 'false':
            kwargs[api.PARAM_DISABLE_ROLLBACK] = False
        else:
            raise ValueError("Unexpected value for parameter %s : %s" %
                             (api.PARAM_DISABLE_ROLLBACK, disable_rollback))
    return kwargs
