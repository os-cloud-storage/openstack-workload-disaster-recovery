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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from horizon import tables, messages
from openstack_dashboard import api
import logging

LOG = logging.getLogger(__name__)
DELETABLE_STATES = ("available", "error")


class UpdateDRPolicyRow(tables.Row):
    ajax = True

    def get_data(self, request, policy_id):
        dr_client = api.dragon.dragonclient(request)
        return dr_client.dr.get_policy_by_id(policy_id)


class TriggerManualPolicy(tables.BatchAction):
    name = "trigger_policy"
    verbose_name = _("Trigger Policy")
    classes = ("btn-create")
    action_present = _("Trigger ")
    action_past = _("Triggered ")
    data_type_singular = _("Policy")
    data_type_plural = ("Policies")

    def action(self, request, workload_policy_id):
        dr_client = api.dragon.dragonclient(request)
        return dr_client.dr.protect(workload_policy_id)


class DeletePolicy(tables.DeleteAction):
    name = "delete"
    action_present = _("Delete ")
    action_past = _("Deleted ")
    data_type_singular = _("Policy")
    data_type_plural = _("Policies")
    classes = ('btn-delete',)

    def delete(self, request, obj_id):
        dr_client = api.dragon.dragonclient(request)
        dr_client.dr.delete_workload_policy(obj_id)


class CreatePolicy(tables.LinkAction):
    name = "add_policy"
    verbose_name = _("Add policy")
    url = "horizon:project:draas:new_policy"
    classes = ("btn-create", "ajax-modal")


class EditPolicy(tables.LinkAction):
    name = "edit_policy"
    verbose_name = _("Edit Policy")
    url = "horizon:project:draas:edit_policy"
    classes = ("btn-edit")


def get_name_from_policy_type(policy):
    return policy['policy_type']['name']


class DRPoliciesTable(tables.DataTable):
    REPL_STATUS_CHOICES = (
        ("enabled", True),
        ("disabled", False),
        ("manual", True),
        ("failed", False),
        ("processing", None),
        (None, False),
    )

    def get_object_id(self, policy):
        return policy['id']

    name = tables.Column('name',
                         link=("horizon:project:draas:edit_policy"),
                         verbose_name=_("Policy Name"))

    class Meta:
        name = "policies"
        verbose_name = _("Protection Policies")
        status_columns = []
        row_class = UpdateDRPolicyRow
        table_actions = [CreatePolicy, DeletePolicy]
        row_actions = [TriggerManualPolicy, EditPolicy]


class EditAction(tables.LinkAction):
    name = "edit_action"
    verbose_name = _("Edit action")
    url = "horizon:project:draas:edit_action"
    classes = ("btn-edit", "ajax-modal")

    def get_link_url(self, resource):
        policy_id = self.table.kwargs['policy_id']
        return reverse(self.url, kwargs={'policy_id': policy_id,
                                 'resource_id': resource['resource']['id'],
                                 'tuple_id': resource['id']})


class AddResourceToPolicy(tables.LinkAction):
    name = "add_resource_to_policy"
    verbose_name = _("Add Resource")
    url = "horizon:project:draas:add_resource_to_policy"
    classes = ("btn-create")

    def get_link_url(self):
        policy_id = self.table.kwargs['policy_id']
        return reverse(self.url, kwargs={'policy_id': policy_id})


class RemoveResourceAction(tables.DeleteAction):
    name = "remove_resource"
    action_present = _("Remove ")
    action_past = _("Removed ")
    data_type_singular = _("Resource")
    data_type_plural = ("Resources")
    classes = ("btn-delete")

    def delete(self, request, obj_id):
        dr_client = api.dragon.dragonclient(request)
        dr_client.dr.delete_resource_action(obj_id)


class DRResourcesTable(tables.DataTable):
    REPL_STATUS_CHOICES = (
        ("selected", True),
        ("unselected", False),
        (None, False),
    )

    def get_object_id(self, resource):
        return resource['id']

    name = tables.Column(lambda row: row['resource']['name'],
                         verbose_name=_("Resource Name"))

    type = tables.Column(lambda row: row['resource']['resource_type']['name'],
                         verbose_name=_("Resource Type"))

    action = tables.Column(lambda row: row['action']['name'],
                         verbose_name=_("Protection Action"))

    class Meta:
        name = "resources"
        verbose_name = _("Policy resources and associated actions")
        status_columns = []
        table_actions = [AddResourceToPolicy]
        row_actions = [EditAction, RemoveResourceAction]
        multi_select = False


class AddResourcesBatch(tables.BatchAction):
    name = "add_resource"
    action_present = _("Add ")
    action_past = _("Added ")
    data_type_singular = _("Resource")
    data_type_plural = ("Resources")
    classes = ("btn-create")

    def allowed(self, request, instance=None):
        return True

    def action(self, request, obj_id):
        obj = self.table.get_object_by_id(obj_id)
        name = obj['name']
        dr_client = api.dragon.dragonclient(request)
        # FIXME: fix this hack and decide whether
        # to use db or enum for resource types
        resource_type_id = 1  # instance?
        if obj['type'] == 'Volume':
            resource_type_id = 2
        # first we try to create the resource,
        # this might fail if the resource exists already in the db
        try:
            dr_client.dr.create_resource(obj_id, name, resource_type_id)
        except:
            logging.warn("Failed creating resource," +
                              " does it exist already?")
        logging.info("Associating resource to its default action")
        # then we associate the resource to its default action in this policy
        action = dr_client.dr \
            .get_default_action_for_resource_type(resource_type_id)
        policy_id = self.table.kwargs['policy_id']
        try:
            dr_client.dr. \
            create_resource_action(obj_id, action['id'], policy_id)
        except:
            messages.error(request, "Could not associate resource to policy")


class AddResourcesToPolicyTable(tables.DataTable):

    def get_object_id(self, resource):
        return resource['id']

    name = tables.Column('name',
                         verbose_name=_("Resource Name"))

    type = tables.Column('type',
                         verbose_name=_("Resource Type"))

    class Meta:
        name = "resources"
        verbose_name = _("Resources not associated to policy")
        status_columns = []
        table_actions = [AddResourcesBatch]
        row_actions = []


class ExecutionDetailsAction(tables.LinkAction):
    name = "show_execution_details"
    verbose_name = _("Details")
    url = "horizon:project:draas:policy_execution"
    classes = ("btn-edit")

    def get_link_url(self, policy_execution):
        policy_id = self.table.kwargs['policy_id']
        return reverse(self.url,
                       kwargs={'policy_id': policy_id,
                         'policy_execution_id': policy_execution['id']})


class PolicyExecutionsTable(tables.DataTable):

    def get_object_id(self, resource):
        return resource['id']

    created_at = tables.Column('created_at',
                         verbose_name=_("Created at"))

    status = tables.Column('status',
                         verbose_name=_("Status"))

    class Meta:
        name = "executions"
        verbose_name = _("Policy Executions")
        status_columns = []
        table_actions = []
        row_actions = [ExecutionDetailsAction]


class PolicyExecutionActionsTable(tables.DataTable):

    def get_object_id(self, resource):
        return resource['id']

    timestamp = tables.Column('created_at',
                         verbose_name=_("Timestamp"))

    resource = tables.Column(lambda action_ex: action_ex['resource']['name'],
                         verbose_name=_("Resource"))

    action = tables.Column(lambda action_ex: action_ex['action']['name'],
                         verbose_name=_("Action"))

    status = tables.Column('status',
                         verbose_name=_("Status"))

    class Meta:
        name = "exec_actions"
        verbose_name = _("Policy Execution Actions")
        status_columns = []
        table_actions = []
        row_actions = []
