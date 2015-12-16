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

from webob import exc
from dragon.common import wsgi
from dragon.rpc import client as rpc_client
from dragon.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class DRController(object):
    """
    WSGI controller for Actions in Heat v1 API
    Implements the API for stack actions
    """

    def __init__(self, options):
        self.options = options
        self.engine = rpc_client.EngineClient()

    def protect(self, req, workload_policy_id, **kwargs):
        context = req.context
        body = kwargs['body']
        return self.engine.protect(context, workload_policy_id,
                                   body['consistent'])

    def recover(self, req, **kwargs):
        context = req.context
        body = kwargs['body']
        if 'container_name' in body:
            return self.engine.failover(context, body['container_name'])
        else:
            err_reason = \
                "Not in valid format, missing container_name in POST body"
            raise exc.HTTPBadRequest(err_reason)

    def failback(self, req, **kwargs):
        context = req.context
        body = kwargs['body']

        if 'container_name' in body:
            return self.engine.faiback(context, body['container_name'])

        else:
            err_reason = \
                "Not in valid format, missing container_name in POST body"
            raise exc.HTTPBadRequest(err_reason)

    def list_actions(self, req, resource_type_id, **kwargs):
        context = req.context
        actions = self.engine.list_actions(context, resource_type_id)

        return actions

    def get_resource(self, req, resource_id, **kwargs):
        context = req.context
        return self.engine.get_resource(context, resource_id)

    def list_resources(self, req, **kwargs):
        context = req.context
        return self.engine.list_resources(context)

    def create_resource(self, req, **kwargs):
        context = req.context
        body = kwargs['body']

        if 'tenant_id' in body and 'resource_name' in body and \
                'resource_type_id' in body and 'resource_id' in body:
            resource_values = {
                'tenant_id': body['tenant_id'],
                'name': body['resource_name'],
                'resource_type_id': body['resource_type_id'],
                'id': body['resource_id'],
            }
            return self.engine.create_resource(context, resource_values)

        else:
            err_reason = "Not in valid format, missing tenant_id /" \
                " resource name / resource type id in the parameters"
            raise exc.HTTPBadRequest(err_reason)

    def list_resource_types(self, req, **kwargs):
        context = req.context
        return self.engine.list_resource_types(context)

    def create_workload_policy(self, req, **kwargs):
        context = req.context
        body = kwargs['body']
        if 'tenant_id' in body and 'name' in body:
            policy_values = {
                'tenant_id': body['tenant_id'],
                'name': body['name'],
            }

            return self.engine.create_workload_policy(context, policy_values)
        else:
            err_reason = "Not in valid format, missing tenant_id /" \
                         "policy id in parameters"
            raise exc.HTTPBadRequest(err_reason)

    def list_workload_policies(self, req, **kwargs):
        context = req.context
        policies = self.engine.list_workload_policies(context)
        return policies

    def get_workload_policy(self, req, workload_policy_id, **kwargs):
        context = req.context
        return self.engine.get_workload_policy(context, workload_policy_id)

    def delete_workload_policy(self, req, workload_policy_id, **kwargs):
        context = req.context
        return self.engine.delete_workload_policy(context, workload_policy_id)

    def get_default_action_for_resource_type(self, req, resource_type_id,
                                             **kwargs):
        context = req.context
        return (self.engine.
                get_default_action_for_resource_type(context,
                                                     resource_type_id))

    def set_resource_action(self, req, resource_id, **kwargs):
        context = req.context
        body = kwargs['body']
        LOG.debug("api/openstack/v1/dr.py: set_resource_action %s %s %s ",
                  (resource_id, body['action_id'], body['workload_policy_id']))
        if 'workload_policy_id' in body and 'action_id' in body:
            return self.engine.set_resource_action(context, resource_id,
                                                   body['action_id'],
                                                   body['workload_policy_id'])
        else:
            err_reason = "Not in valid format, missing workload_policy_id or "\
                         "action_id in parameters"
            raise exc.HTTPBadRequest(err_reason)

    def update_resource_action(self, req, workload_policy_id, resource_id,
                               tuple_id, **kwargs):
        context = req.context
        body = kwargs['body']
        if 'workload_policy_id' in body and 'action_id' in body:
            return self.engine.update_resource_action(context,
                                                      workload_policy_id,
                                                      resource_id,
                                                      tuple_id,
                                                      body['action_id'])
        else:
            err_reason = "Not in valid format, " \
                "missing workload_policy_id or action_id in parameters"
            raise exc.HTTPBadRequest(err_reason)

    def delete_resource_action(self, req, tuple_id, **kwargs):
        context = req.context
        return self.engine.delete_resource_action(context, tuple_id)

    def get_policy_resource_actions(self, req, workload_policy_id, **kwargs):
        context = req.context
        return self.engine.get_policy_resource_actions(context,
                                                       workload_policy_id)

    def get_policy_resource_action(self, req, workload_policy_id,
                                   resource_id, **kwargs):
        context = req.context
        return self.engine.get_policy_resource_action(context,
                                                      workload_policy_id,
                                                      resource_id)

    def list_policy_executions(self, req, workload_policy_id, **kwargs):
        context = req.context
        return self.engine.list_policy_executions(context, workload_policy_id)

    def get_policy_executions(self, req, policy_execution_id, **kwargs):
        context = req.context
        return self.engine.get_policy_executions(context, policy_execution_id)

    def get_policy_execution_actions(self, req, policy_execution_id, **kwargs):
        context = req.context
        return self.engine.get_policy_execution_actions(context,
                                                        policy_execution_id)

    def recovery_list_policies(self, req, **kwargs):
        return self.engine.recovery_list_policies(req.context)

    def recovery_list_policy_executions(self, req, policy_name, **kwargs):
        return self.engine.recovery_list_policy_executions(req.context,
                                                           policy_name)


def create_resource(options):
    deserializer = wsgi.JSONRequestDeserializer()
    serializer = wsgi.JSONResponseSerializer()
    return wsgi.Resource(DRController(options), deserializer, serializer)
