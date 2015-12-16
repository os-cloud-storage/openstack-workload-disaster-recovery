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

from dragon.common import messaging
from dragon.rpc import api
from dragon.openstack.common import log as logging

LOG = logging.getLogger(__name__)

"""
Client side of the heat engine RPC API.
"""


class EngineClient(object):
    '''Client side of the heat engine rpc API.

    API version history:

        1.0 - Initial version.
    '''

    BASE_RPC_API_VERSION = '1.0'

    def __init__(self):
        self._client = messaging.get_rpc_client(
            topic=api.ENGINE_TOPIC,
            version=self.BASE_RPC_API_VERSION)

    @staticmethod
    def make_msg(method, **kwargs):
        return method, kwargs

    def call(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.call(ctxt, method, **kwargs)

    def cast(self, ctxt, msg, version=None):
        method, kwargs = msg
        if version is not None:
            client = self._client.prepare(version=version)
        else:
            client = self._client
        return client.cast(ctxt, method, **kwargs)

    def get_marked_dr_instances(self, context):
        filters = {'filter': [{'name': 'tag:dr_state',
                               'value': ['marked for DR']}]}

        # TODO(): nova api or local db store
        return self.db.instance_get_all_by_filters(context, filters)

    def protect(self, context, workload_policy_id, consistent):
        LOG.debug("compute api protect")
        return self.cast(context,
                         self.make_msg('protect',
                                       workload_policy_id=workload_policy_id,
                                       consistent=consistent))

    def failover(self, context, container_name):
        LOG.debug("compute api recover")
        return self.cast(context,
                         self.make_msg('failover',
                                       container_name=container_name))

    def failback(self, context, container_name):
        LOG.debug("compute api failback")
        return self.cast(context,
                         self.make_msg('failback',
                                       container_name=container_name))

    def list_actions(self, context, resource_type):
        LOG.debug("dragon api list_actions")
        return self.call(context,
                         self.make_msg('list_actions',
                                       resource_type=resource_type))

    def get_default_action_for_resource_type(self, context, resource_type):
        LOG.debug("dragon api get_default_action_for_resource_type-policies")
        return self.call(context,
                         self.make_msg('get_default_action_for_resource_type',
                                       resource_type_id=resource_type))

    def get_resource(self, context, resource_id):
        LOG.debug("dragon api get_resource")
        return self.call(context,
                         self.make_msg('get_resource',
                                       resource_id=resource_id))

    def list_resources(self, context):
        LOG.debug("dragon api list-resources")
        return self.call(context, self.make_msg('list_resources'))

    def create_resource(self, context, values):
        LOG.debug("dragon api create_resource")
        return self.call(context,
                         self.make_msg('create_resource',
                                       values=values))

    def create_workload_policy(self, context, values):
        LOG.debug("dragon api create_workload_policy")
        return self.call(context, self.make_msg('create_workload_policy',
                                                values=values))

    def list_workload_policies(self, context):
        LOG.debug("dragon api list_workload_policies")
        return self.call(context, self.make_msg('list_workload_policies'))

    def get_workload_policy(self, context, workload_policy_id):
        LOG.debug("dragon api get_workload_policy")
        return self.call(context,
                         self.make_msg('get_workload_policy',
                                       workload_policy_id=workload_policy_id))

    def delete_workload_policy(self, context, workload_policy_id):
        LOG.debug("dragon api get_workload_policy")
        return self.call(context,
                         self.make_msg('delete_workload_policy',
                                       workload_policy_id=workload_policy_id))

    def set_resource_action(self, context, resource_id, action_id,
                            workload_policy_id):
        LOG.debug("dragon api set_resource_action")
        return self.call(context,
                         self.make_msg('set_resource_action',
                                       resource_id=resource_id,
                                       action_id=action_id,
                                       workload_policy_id=workload_policy_id))

    def update_resource_action(self, context, workload_policy_id, resource_id,
                               tuple_id, action_id):
        LOG.debug("dragon api update_resource_action")
        return self.call(context,
                         self.make_msg('update_resource_action',
                                       workload_policy_id=workload_policy_id,
                                       resource_id=resource_id,
                                       tuple_id=tuple_id,
                                       action_id=action_id))

    def delete_resource_action(self, context, tuple_id):
        LOG.debug("dragon api delete_resource_action")
        return self.call(context,
                         self.make_msg('delete_resource_action',
                                       tuple_id=tuple_id))

    def get_policy_resource_actions(self, context, workload_policy_id):
        LOG.debug("dragon api get_policy_resource_actions")
        return self.call(context,
                         self.make_msg('get_policy_resource_actions',
                                       workload_policy_id=workload_policy_id))

    def get_policy_resource_action(self, context, workload_policy_id,
                                   resource_id):
        LOG.debug("dragon api get_policy_resource_action")
        return self.call(context,
                         self.make_msg('get_policy_resource_action',
                                       workload_policy_id=workload_policy_id,
                                       resource_id=resource_id))

    def list_policy_executions(self, context, workload_policy_id):
        LOG.debug("dragon api list_policy_executions")
        return self.call(context,
                         self.make_msg('list_policy_executions',
                                       workload_policy_id=workload_policy_id))

    def get_policy_executions(self, context, policy_execution_id):
        LOG.debug("dragon api get_policy_executions")
        return self.call(
            context,
            self.make_msg('get_policy_executions',
                          policy_execution_id=policy_execution_id))

    def get_policy_execution_actions(self, context, policy_execution_id):
        LOG.debug("dragon api get_policy_execution_actions")
        return self.call(
            context,
            self.make_msg('get_policy_execution_actions',
                          policy_execution_id=policy_execution_id))

    def recovery_list_policies(self, context):
        LOG.debug("dragon api recovery_list_policies")
        return self.call(context, self.make_msg('recovery_list_policies'))

    def recovery_list_policy_executions(self, context, policy_name):
        LOG.debug("dragon api recovery_list_policy_executions")
        return self.call(context,
                         self.make_msg('recovery_list_policy_executions',
                                       policy_name=policy_name))
