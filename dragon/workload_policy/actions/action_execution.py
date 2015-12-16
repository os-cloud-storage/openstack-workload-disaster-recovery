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

from dragon.openstack.common import log as logging
from dragon.db import api as db_api

LOG = logging.getLogger(__name__)


class ActionExecution(object):

    def __init__(self, workload_action_excution_id, resource_id, action_id):
        self.workload_action_excution_id = workload_action_excution_id
        self.resource = resource_id
        self.id = action_id

    def set_status(self, context, new_status):
        action_execution_status = {
            'workload_policy_execution_id': self.workload_action_excution_id,
            'action_id': self.id,
            'resource_id': self.resource,
            'status': new_status,
        }
        db_api.action_excution_create(context, action_execution_status)
