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

import functools

from oslo.config import cfg
from oslo import messaging

from dragon.common import context
from dragon.common import messaging as rpc_messaging
from dragon.db import api as db_api
from dragon.engine.clients import Clients
from dragon.openstack.common import log as logging
from dragon.openstack.common.gettextutils import _
from dragon.openstack.common import service
from dragon.workload_policy import workload_policy as wp
from swiftclient.exceptions import ClientException

LOG = logging.getLogger(__name__)


def request_context(func):
    @functools.wraps(func)
    def wrapped(self, ctx, *args, **kwargs):
        if ctx is not None and not isinstance(ctx, context.RequestContext):
            ctx = context.RequestContext.from_dict(ctx.to_dict())
        return func(self, ctx, *args, **kwargs)
    return wrapped


class EngineService(service.Service):
    """
    Manages the running instances from creation to destruction.
    All the methods in here are called from the RPC backend.  This is
    all done dynamically so if a call is made via RPC that does not
    have a corresponding method here, an exception will be thrown when
    it attempts to call into this class.  Arguments to these methods
    are also dynamically added and will be named as keyword arguments
    by the RPC caller.
    """

    RPC_API_VERSION = '1.1'

    def __init__(self, host, topic, manager=None):
        super(EngineService, self).__init__()
        self.stg = {}
        self.clients = None
#        self.engine_id = None
        self.target = None
        self.host = host
        self.topic = topic

    def _service_task(self):
        """
        This is a dummy task which gets queued on the service.Service
        threadgroup.  Without this service.Service sees nothing running
        i.e has nothing to wait() on, so the process exits..
        This could also be used to trigger periodic non-stack-specific
        housekeeping tasks
        """
        pass

    def start(self):
        target = messaging.Target(
            version=self.RPC_API_VERSION, server=cfg.CONF.host,
            topic=self.topic)
        self.target = target
        server = rpc_messaging.get_rpc_server(target, self)
        server.start()

        super(EngineService, self).start()

        # Create dummy service task, because when there is nothing queued
        # on self.tg the process exits
        self.tg.add_timer(cfg.CONF.periodic_interval,
                          self._service_task)

    def stop(self):
        # Stop rpc connection at first for preventing new requests
        LOG.info(_("Attempting to stop engine service..."))
        try:
            self.conn.close()
        except Exception:
            pass
        super(EngineService, self).stop()

    @request_context
    def protect(self, cnxt, workload_policy_id, consistent):
        LOG.debug("In service.protect , consistent- %s" % consistent)
        workload_policy = wp.WorkloadPolicy(cnxt, workload_policy_id,
                                            consistent)
        return workload_policy.protect(cnxt)

    @request_context
    def failover(self, cnxt, container_name):
        container_fields = container_name.split("/")
        return wp.WorkloadPolicy.failover(cnxt, container_name)

    @request_context
    def list_actions(self, cnxt, resource_type):
        return db_api.action_get_by_resource_type(cnxt, resource_type)

    @request_context
    def get_default_action_for_resource_type(self, cnxt, resource_type_id):
        LOG.debug("dragon get_default_action_for_resource_type %s"
                  % resource_type_id)
        return db_api.action_get_default_by_resource_type(
            cnxt, resource_type_id)

    @request_context
    def get_resource(self, cnxt, resource_id):
        return db_api.resource_get(cnxt, resource_id)

    @request_context
    def list_resources(self, cnxt):
        return db_api.resource_get_all(cnxt, cnxt.tenant_id)

    @request_context
    def create_resource(self, cnxt, values):
        return db_api.resource_create(cnxt, values)

    @request_context
    def create_workload_policy(self, cnxt, values):
        return db_api.workload_policy_create(cnxt, values)

    @request_context
    def list_workload_policies(self, cnxt):
        return db_api.workload_policy_get_all(cnxt, cnxt.tenant_id)

    @request_context
    def get_workload_policy(self, cnxt, workload_policy_id):
        return db_api.workload_policy_get(cnxt, workload_policy_id)

    @request_context
    def delete_workload_policy(self, cnxt, workload_policy_id):
        return db_api.workload_policy_delete(cnxt, workload_policy_id)

    @request_context
    def set_resource_action(self, cnxt, resource_id, action_id,
                            workload_policy_id):
        values = {"resource_id": resource_id, "action_id": action_id,
                  "workload_policy_id": workload_policy_id}
        return db_api.resource_actions_create(cnxt, values)

    @request_context
    def update_resource_action(self, cnxt, workload_policy_id, resource_id,
                               tuple_id, action_id):
        values = {"resource_id": resource_id, "action_id": action_id,
                  "workload_policy_id": workload_policy_id}
        return db_api.resource_actions_update(cnxt, tuple_id, values)

    @request_context
    def delete_resource_action(self, cnxt, tuple_id):
        return db_api.resource_actions_delete(cnxt, tuple_id)

    @request_context
    def delete_resource_actions(self, cntx, workload_policy_id):
        return db_api.resource_actions_delete_all_by_policy_id(
            cntx,
            workload_policy_id)

    @request_context
    def get_policy_resource_actions(self, cnxt, workload_policy_id):
        return db_api.resource_actions_get_by_workload(cnxt,
                                                       workload_policy_id)

    @request_context
    def get_policy_resource_action(self, cnxt, workload_policy_id,
                                   resource_id):
        LOG.debug("dragon get_policy_resource_action %s %s"
                  % (workload_policy_id, resource_id))
        return db_api.resource_actions_get(cnxt, workload_policy_id,
                                           resource_id)

    @request_context
    def list_policy_executions(self, cnxt, workload_policy_id):
        return db_api.workload_policy_excution_get_by_workload(
            cnxt, workload_policy_id)

    @request_context
    def get_policy_executions(self, cnxt, policy_execution_id):
        return db_api.workload_policy_excution_get(cnxt, policy_execution_id)

    @request_context
    def get_policy_execution_actions(self, cnxt, policy_execution_id):
        return db_api.workload_policy_excution_actions_get(cnxt,
                                                           policy_execution_id)

    @request_context
    def recovery_list_policies(self, cntx):
        tenant_name = cntx.tenant
        try:
            headers, containers = Clients(cntx).swift().get_account(
                prefix=tenant_name, full_listing=True)
            # TOF: since cinder backup restore wants containers
            # (and not pseudo-containers)
            # we have to create a container for each policy execution.
            # Here we're doing a sort of hack to derive policy names from
            # container names in this form:
            # tenant_policyName_executionTimeStamp (e.g.,
            # admin_instance_only_20140825140210)
            # get policy names
            policies = {}
            for container in containers:
                try:
                    [policy_name, timestamp] =\
                        wp.get_policy_name_and_timestamp_from_container(
                            tenant_name, container['name'])
                    policies[policy_name] = {'id': policy_name,
                                             'name': policy_name,
                                             "timestamp": timestamp}
                except Exception, e:
                    # keep going
                    LOG.warn(e)
            # convert dict to list
            policies = policies.values()
            return policies
        except ClientException, c:
            if c.http_status == 404:
                # TOF: I wonder why they send an exception for a 404.
                # Anyhow, we'll send back an empty list
                return []
            else:
                raise c

    @request_context
    def recovery_list_policy_executions(self, cntx, policy_name):
        LOG.debug("In recovery_list_policy_executions with name: %s"
                  % policy_name)
        tenant_name = cntx.tenant
        headers, containers = Clients(cntx).swift().\
            get_account(prefix=tenant_name + "_" + policy_name,
                        full_listing=True)
        # sort in reverse name order (newer containers first)
        containers.sort(reverse=True, key=lambda k: k['name'])
        policies = []
        # split name and timestamp and put in list of dict
        for container in containers:
                try:
                    [policy_name, timestamp] =\
                        wp.get_policy_name_and_timestamp_from_container(
                            tenant_name, container['name'])
                    policies.append({'id': container['name'],
                                     'name': policy_name,
                                     "timestamp": timestamp})
                except Exception, e:
                    # keep going
                    LOG.warn(e)
        LOG.info("policies: %s" % policies)
        return policies

    @request_context
    def create_resource_type(self, cntx, values):
        return db_api.resource_type_create(cntx, values)

    @request_context
    def resource_type_get_by_name(self, cntx, name):
        return db_api.resource_type_get_by_name(cntx, name)

    @request_context
    def create_action(self, cntx, values):
        return db_api.action_create(cntx, values)

    @request_context
    def delete_action(self, cntx, action_id):
        return db_api.action_delete(cntx, action_id)

    @request_context
    def delete_resource(self, cntx, resource_id):
        return db_api.resource_delete(cntx, resource_id)

    @request_context
    def list_resource_types(self, cntx):
        return db_api.resource_type_get_all(cntx)

    @request_context
    def workload_policy_excution_create(self, cntx, values):
        return db_api.workload_policy_excution_create(cntx, values)

    @request_context
    def workload_policy_excution_get_by_workload(self, cntx,
                                                 workload_policy_id):
        return db_api.workload_policy_excution_get_by_workload(
            cntx,
            workload_policy_id)

    @request_context
    def workload_policy_execution_delete(self, cntx, workload_policy_exec_id):
        return db_api.workload_policy_execution_delete(cntx,
                                                       workload_policy_exec_id)

    @request_context
    def action_excution_delete_all_by_policy_exec(self,
                                                  cntx,
                                                  workload_policy_exe_id):
        return db_api.action_excution_delete_all_by_policy_exec(
            cntx,
            workload_policy_exe_id)
