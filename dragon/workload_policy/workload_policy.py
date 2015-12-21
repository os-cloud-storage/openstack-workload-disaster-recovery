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

from eventlet import greenthread
import re
import sys
import traceback

from dragon.openstack.common import log as logging
from dragon.openstack.common import timeutils
from dragon.openstack.common import jsonutils
from dragon.db import api
from dragon.engine.clients import Clients
from dragon.workload_policy.actions import action
from dragon.common import exception
# TODO(Oshrit): load dynamically
from dragon.template import heat_flame_template
from dragon.template.heat_template import KeyPairResource

LOG = logging.getLogger(__name__)


def get_policy_execution_container_name(tenant_name, policy_name):
    timestamp = timeutils.strtime(fmt="%Y%m%d%H%M%S")
    # add timestamp and policy prefix
    return tenant_name + "_" + policy_name + "_" + timestamp


def get_global_container_name(tenant_name, policy_name):
    return tenant_name + "_global"


def get_policy_name_and_timestamp_from_container(tenant_name, container_name):
    policy_regex = re.compile(r"^" + tenant_name +
                              "_([a-zA-Z0-9_]+)_([0-9]+)$")
    match = policy_regex.match(container_name)
    if match:
        timestamp = timeutils.parse_strtime(match.group(2), fmt="%Y%m%d%H%M%S")
        return [match.group(1), timestamp]
    else:
        raise Exception("Container name does not reflect policy_execution\
                        convention for names")


class WorkloadPolicy(object):

    def __init__(self, cntx, workload_policy_id, consistent_protect):
        self.id = workload_policy_id
        # retrieve action and resource list from database
        workload_policy = api.workload_policy_get(cntx, self.id)
        self.actions = api.resource_actions_get_by_workload(cntx, self.id)
        self.name = workload_policy.name
        self.consistent_protect = consistent_protect

    def pre_protect(self, cnxt, workload_action_excution):
        for db_action in self.actions:
            # instantiate action class
            action_obj = action.load(db_action, context=cnxt)

            # invoke protect method on action class passing resource id
            action_obj.pre_protect(cnxt, workload_action_excution.id,
                                   db_action.resource.id)

    def protect(self, cnxt):
        # Define container_name, Swift create if container does not exists
        container_name = get_policy_execution_container_name(cnxt.tenant,
                                                             self.name)
        swift_conn = Clients(cnxt).swift()
        # container = swift.swift_create_container(request, name)
        headers = {'X-Container-Meta-dr_state': 'processing'}
        swift_conn.put_container(container_name, headers)
        LOG.debug("put_container %s " % (container_name))

        # Create a global container for the tenant in case it does not exists
        if action.Action.is_using_global_container:
            swift_conn.put_container(get_global_container_name(cnxt.tenant,
                                                               self.name),
                                     {'X-Container-Meta-dr_state': 'ready'})

        # create workload_policy_execution instance
        protect_execution = {'workload_policy_id': self.id,
                             'status': 'Creating',
                             }
        workload_action_excution =\
            api.workload_policy_excution_create(cnxt, protect_execution)
        # TODO(load dynamic)
        template_generator = heat_flame_template.HeatFlameTemplate(cnxt)

        try:
            if self.consistent_protect:
                self.pre_protect(cnxt, workload_action_excution)

            # iterate on actions
            protect_statuses = []
            metadata = {}
            metadata["workload_policy_name"] = self.name
            policy_status = True
            metadata["actions"] = []
            for db_action in self.actions:
                try:
                    # instantiate action class
                    action_obj = action.load(db_action, context=cnxt)

                    if action_obj.is_using_global_container():
                        action_container_name =\
                            get_global_container_name(cnxt.tenant, self.name)
                    else:
                        action_container_name = container_name

                    # invoke protect method on action class passing resource id
                    status, protect_data =\
                        action_obj.protect(cnxt, workload_action_excution.id,
                                           db_action.resource.id,
                                           action_container_name)

                    policy_status = policy_status and (status == "Protected")

                    action_obj.generate_template(cnxt, template_generator)

                    # save result of invocation in relation
                    # to workload_policy_execution
                    protect_statuses.\
                        append({"action id": db_action.action.id,
                                "action_name": db_action.action.name,
                                "resource_id": db_action.resource.id,
                                "resource_name": db_action.resource.name,
                                "status": status})

                    db_action.execution_data = protect_data
                    metadata["actions"].append(db_action)
                    LOG.debug("action metadata %s " % (metadata))
                except Exception, e:
                    policy_status = False
                    exc = sys.exc_info()
                    LOG.error(traceback.format_exception(*exc))
                    LOG.error("resource %s could not be protected using action"
                              "%s. Verify that the resource is a valid Nova"
                              " resource"
                              % (db_action.resource.id, db_action.action.name))
        except Exception, e:
            policy_status = False
            LOG.debug(e)
            LOG.error("Workload could not be protected")
        finally:
            if self.consistent_protect:
                try:
                    self.post_protect(cnxt, workload_action_excution)
                except Exception, ex:
                    LOG.debug(ex)

            if policy_status:
                status = "Protected"  # TODO(Oshrit): change to final
            else:
                status = "Error"
            LOG.debug("workload_policy_execution_set_status %s with status %s"
                      % (workload_action_excution.id, status))

            api.workload_policy_execution_set_status(
                cnxt,
                workload_action_excution.id,
                status)

            # save workload_policy_execution log
            swift_conn.put_object(container_name,
                                  "workload_policy_execution.log",
                                  jsonutils.dumps(protect_statuses))

        # save metadata to container
        swift_conn.put_object(container_name, "metadata",
                              jsonutils.dumps(metadata))

        swift_conn.put_object(container_name, "template.yaml",
                              template_generator.get_template())

        headers = {'X-Container-Meta-dr_state': 'ready'}
        swift_conn.post_container(container_name, headers)

        return policy_status

    def post_protect(self, cnxt, workload_action_excution):
        for db_action in self.actions:
            # instantiate action class
            action_obj = action.load(db_action, context=cnxt)

            # invoke protect method on action class passing resource id
            action_obj.post_protect(cnxt,
                                    workload_action_excution.id,
                                    db_action.resource.id)

    def generate_template(self, context):
        raise NotImplementedError

    @staticmethod
    def _post_heat_stack_creation(context, heat, stack_id):
        static_resource_type_mapping = {"OS::Cinder::Volume": "volume",
                                        "OS::Nova::Server": "instance"}
        mapping = {}
        stack_status = heat.stacks.get(stack_id)
        LOG.debug("stack status %s" % stack_status)
        while (stack_status.stack_status == "CREATE_IN_PROGRESS"):
            greenthread.sleep(5)
            stack_status = heat.stacks.get(stack_id)
        if (stack_status.stack_status != "CREATE_COMPLETE"):
            raise exception.OrchestrationError(reason=stack_status.
                                               stack_status_reason)
        stack_resources = heat.resources.list(stack_id)
        stack_obj = heat.resources
        stack_events = heat.events
        for stack_resource in stack_resources:
            if stack_resource.resource_type in static_resource_type_mapping:
                resource_events =\
                    stack_events.list(stack_id,
                                      stack_resource.resource_name)
                for resource_event in resource_events:
                    resource_event_data =\
                        stack_events.get(stack_id,
                                         stack_resource.resource_name,
                                         resource_event.id)

                    if resource_event.resource_status == "CREATE_COMPLETE":
                        resource_name =\
                            resource_event_data.resource_properties["name"]

                        rt = stack_resource.resource_type
                        mapping[(resource_name,
                                 static_resource_type_mapping[rt])] =\
                            stack_resource.physical_resource_id
        return mapping

    @staticmethod
    def _restoreMetadataDB(context, metadata, stack_resources):
        workload_policy_name = metadata["workload_policy_name"]
        workload_policy_obj = {
            'name': workload_policy_name,
            'tenant_id': context.tenant_id,
        }
        workload_policy = api.workload_policy_create(context,
                                                     workload_policy_obj)

        for restore_action in metadata["actions"]:
            # Create action-resource relationships,
            # New resources IDs from Heat orchestration
            action_resource = restore_action["resource"]
            action_name = action_resource["name"]
            action_rsc_name = action_resource["resource_type"]["name"]
            new_resource_id = stack_resources[(action_name, action_rsc_name)]
            resource_obj =\
                {'id': new_resource_id,
                 'name': action_name,
                 'resource_type_id': action_resource["resource_type_id"],
                 'tenant_id': context.tenant_id
                 }
            api.resource_create(context, resource_obj)

            db_action = restore_action["action"]
            resource_action_obj = {
                'workload_policy_id': workload_policy.id,
                'resource_id': new_resource_id,
                'action_id': db_action['id'],
            }
            api.resource_actions_create(context, resource_action_obj)

    @staticmethod
    def failover(context, container_name):
        swift_conn = Clients(context).swift()
        LOG.debug("failover container name %s" % (container_name))
        # TODO(Oshrit): load dynamically
        template_generator = heat_flame_template.HeatFlameTemplate(context)

        # Loop over metadata file, load actions
        swift_meta, actions_metadata = swift_conn.get_object(container_name,
                                                             "metadata")
        actions = jsonutils.loads(actions_metadata)
        policy_status = False
        try:
            for recover_action in actions["actions"]:
                action_resource = recover_action["resource"]
                db_action = recover_action["action"]
                action_extra_data = recover_action["execution_data"]

                # Instantiate action class
                action_obj = action.load_action_driver(db_action["class_name"],
                                                       context=context)

                if action_obj.is_using_global_container():
                    action_container_name =\
                        get_global_container_name(context.tenant, "")
                else:
                    action_container_name = container_name

                # Invoke recover method on action class passing resource id
                policy_status = action_obj.failover(context,
                                                    action_resource["id"],
                                                    action_extra_data,
                                                    action_container_name)

                # Invoke failover for each resource-action
                action_obj.generate_template(context, template_generator)

        except Exception, e:
            policy_status = False
            LOG.debug(e)
            LOG.error("resource %s could not be recovered using action %s."
                      "Verify that the resource is a valid Nova resource"
                      % (db_action["id"], db_action["name"]))

        if not policy_status:
            return policy_status

        keypairs = Clients(context).nova().keypairs.list()
        for keypair in keypairs:
            template_generator.add_keypair(KeyPairResource(keypair.name))

        # TODO(Oshrit): no need to run HEAT if one of the
        # resources failed to restore
        swift_meta, template = swift_conn.get_object(container_name,
                                                     "template.yaml")
        LOG.debug("template.yaml = %s " % template)
        adjusted_template =\
            template_generator.process_recover_template(template)

        LOG.debug("adjusted template = %s " % adjusted_template)

        stack_name = container_name

        fields = {
            'stack_name': stack_name,
            'timeout_mins': 15,
            'disable_rollback': True,
            # 'parameters': dict(params_list),
            'password': "passw0rd"
        }
        fields['template'] = adjusted_template

        # Call heat to restore stack from template.yaml
        stack = Clients(context).heat().stacks.create(**fields)

        # Wait for template to complete
        stack_created_resources =\
            WorkloadPolicy._post_heat_stack_creation(context,
                                                     Clients(context).heat(),
                                                     stack["stack"]["id"])

        # Create DB entries for tenant (restore from metadata)
        WorkloadPolicy._restoreMetadataDB(context, actions,
                                          stack_created_resources)
        # clean stack - decided to be admin manual

        return policy_status


def get_workload_policy_by_name(context, policy_name):
    all_policies = api.workload_policy_get_all(context, context.tenant_id)
    LOG.debug("Searching for policy %s" % policy_name)

    for policy in all_policies:
        if policy.name == policy_name:
            return policy
