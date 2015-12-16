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

from .forms import AddPolicyForm, EditActionForm
from .tables import DRPoliciesTable, DRResourcesTable, \
    AddResourcesToPolicyTable, PolicyExecutionsTable, \
    PolicyExecutionActionsTable
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions, forms, messages, tables
from horizon.utils import memoized
from openstack_dashboard.api import dragon
from openstack_dashboard.dashboards.project.volumes.tabs \
    import VolumeTableMixIn
import logging

LOG = logging.getLogger(__name__)


class AddPolicyView(forms.ModalFormView):
    form_class = AddPolicyForm
    template_name = 'project/draas/policies/create_policy.html'
    success_url = reverse_lazy("horizon:project:draas:index")


class EditActionView(forms.ModalFormView):
    form_class = EditActionForm
    template_name = 'project/draas/actions/choose.html'

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        super(EditActionView, self).get_initial()
        self.initial.update(self.kwargs)
        return self.initial.copy()

    def get_success_url(self):
        form = self.get_form(self.form_class)
        policy_id = form.data['policy_id_input']
        return reverse_lazy("horizon:project:draas:edit_policy",
                            kwargs={'policy_id': policy_id})


class PolicyView(tables.MultiTableView):
    template_name = 'project/draas/policies/detail.html'
    table_classes = (DRResourcesTable, PolicyExecutionsTable)

    def get_resources_data(self):
        try:
            dr_client = dragon.dragonclient(self.request)
            policy_id = self.kwargs['policy_id']
            resources = dr_client.dr.get_policy_resource_actions(policy_id)
            logging.warn("Resources: %s" % resources)
            return resources
        except Exception as e:
            messages.error(self.request, "cannot get resources from dragon")
            LOG.error(e)
            return []

    def get_executions_data(self):
        try:
            dr_client = dragon.dragonclient(self.request)
            policy_id = self.kwargs['policy_id']
            executions = dr_client.dr.list_policy_executions(policy_id)
            logging.warn(executions)
            if isinstance(executions, list):
                return executions
            elif isinstance(executions, dict):
                return [executions]
        except:
            messages.error(self.request,
                           "Could not retrieve policy executions")
            logging.exception("Could not retrieve policy executions")

    @memoized.memoized_method
    def _get_data(self):
        try:
            policy_id = self.kwargs['policy_id']
            policy = dragon.dragonclient(self.request).dr \
                .get_workload_policy(policy_id)
        except Exception:
            msg = _('Unable to retrieve details for policy "%s".') \
                % (policy_id)
            exceptions.handle(self.request, msg)
        return policy

    def get_context_data(self, **kwargs):
        context = super(PolicyView, self).get_context_data(**kwargs)
        context["policy"] = self._get_data()
        return context


class PoliciesView(tables.MultiTableView):
    table_classes = (DRPoliciesTable,)
    template_name = "project/draas/policies/index.html"

    def get_policies_data(self):
        try:
            dr_client = dragon.dragonclient(self.request)
            policies = dr_client.dr.list_workload_policies()
            LOG.debug("Policies: %s" % policies)
            return policies
        except Exception as e:
            messages.error(self.request, "cannot get policies from dragon")
            LOG.error(e)
            return []


class AddResourceView(tables.MultiTableView, VolumeTableMixIn):
    table_classes = (AddResourcesToPolicyTable,)
    template_name = "project/draas/resources/index.html"

    def get_volumes_data(self):
        volumes = self._get_volumes()
        return volumes

    def get_instances_data(self):
        instances = self._get_instances()
        return instances

    def get_resources_data(self):
        try:
            policy_id = self.kwargs['policy_id']
            dr_client = dragon.dragonclient(self.request)
            filtered_resources = []
            dr_resources = dr_client.dr.get_policy_resource_actions(policy_id)
            dr_resource_ids = [x['resource_id'] for x in dr_resources]
            instances = self.get_instances_data()
            for instance in instances:
                if instance.id not in dr_resource_ids:
                    filtered_resources.append({'name': instance.name,
                                               'type': 'Instance',
                                               'id': instance.id})
            volumes = self.get_volumes_data()
            for volume in volumes:
                if volume.id not in dr_resource_ids:
                    filtered_resources.append({'name': volume.name,
                                               'type': 'Volume',
                                               'id': volume.id})
            return filtered_resources
        except Exception as e:
            messages.error(self.request, "cannot get resources from dragon")
            LOG.error(e)
            return []

    @memoized.memoized_method
    def _get_data(self):
        try:
            policy_id = self.kwargs['policy_id']
            policy = dragon.dragonclient(self.request).dr \
            .get_workload_policy(policy_id)
        except Exception:
            msg = _('Unable to retrieve details for policy "%s".') \
                % (policy_id)
            exceptions.handle(self.request, msg)
        return policy

    def get_context_data(self, **kwargs):
        context = super(AddResourceView, self).get_context_data(**kwargs)
        context["policy"] = self._get_data()
        return context


class PolicyExecutionView(tables.MultiTableView):
    table_classes = (PolicyExecutionActionsTable,)
    template_name = "project/draas/policies/executions/detail.html"

    def get_exec_actions_data(self):
        try:
            policy_exec_id = self.kwargs['policy_execution_id']
            dr_client = dragon.dragonclient(self.request)
            exec_actions = dr_client.dr \
                .get_policy_execution_actions(policy_exec_id)
            return exec_actions
        except Exception as e:
            messages.error(self.request, "cannot get resources from dragon")
            LOG.error(e)
            return []
