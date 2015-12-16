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

from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions, forms, messages
from openstack_dashboard import api
import re
import logging
LOG = logging.getLogger(__name__)


class AddPolicyForm(forms.SelfHandlingForm):
    name = forms.RegexField(required=True,
            regex=re.compile(r"^[a-zA-Z0-9_]+$"),
            error_message="Policy names can only contain literals and '_'",
            initial="new_policy_name",
            help_text="Name of new policy",
            label="Provide a mnemonic name to the workload protection policy")

    def handle(self, request, data):
        try:
            name = request.POST['name']
            dr_client = api.dragon.dragonclient(request)
            dr_client.dr.create_workload_policy(name, request.user.tenant_id)
            messages.success(request, "Policy added")
            return True
        except ValidationError, e:
            messages.error(request, e.messages[0])
            return False
        except:
            exceptions.handle(request, ignore=False)
            messages.error(request, _("Could not create policy"))
            return False

    def __init__(self, request, *args, **kwargs):
        super(forms.SelfHandlingForm, self).__init__(request, *args, **kwargs)
        self.request = request


class EditActionForm(forms.SelfHandlingForm):
    selected_action = forms.ChoiceField(required=False,
                                        help_text=None,
                                        label="Available Protection Actions")
    # hidden fields
    resource_id_input = forms.CharField(widget=forms.HiddenInput())
    policy_id_input = forms.CharField(widget=forms.HiddenInput())
    tuple_id_input = forms.CharField(widget=forms.HiddenInput())

    def handle(self, request, data):
        try:
            action_id = self.cleaned_data['selected_action']
            LOG.error("Obtained action id: %s" % action_id)
            dr_client = api.dragon.dragonclient(request)
            policy_id = self.cleaned_data['policy_id_input']
            resource_id = self.cleaned_data['resource_id_input']
            tuple_id = self.cleaned_data['tuple_id_input']
            dr_client.dr.update_resource_action(policy_id,
                                                resource_id,
                                                tuple_id, action_id)
            messages.success(request, "Action selected")
            return True
        except ValidationError, e:
            messages.error(request, e.messages[0])
            return False
        except:
            exceptions.handle(request, ignore=False)
            messages.error(request, _("Could not set action"))
            return False

    def __init__(self, request, *args, **kwargs):
        super(EditActionForm, self).__init__(request, *args, **kwargs)
        try:
            dr_client = api.dragon.dragonclient(request)
            if (request.method == "GET"):
                initial = kwargs['initial']
                resource_id = initial['resource_id']
                policy_id = initial['policy_id']
                tuple_id = initial['tuple_id']
                self.fields['policy_id_input'].initial = policy_id
                self.fields['resource_id_input'].initial = resource_id
                self.fields['tuple_id_input'].initial = tuple_id
                previously_selected_action = dr_client.dr \
                    .get_policy_resource_action(policy_id, resource_id)
                self.fields['selected_action'].initial = (
                            previously_selected_action)
            else:
                resource_id = request.POST['resource_id_input']
            resource = dr_client.dr.get_resource(resource_id)
            logging.warn(resource)
            resource_type_id = resource['resource_type_id']
            choices = []
            action_types = dr_client.dr.list_actions(resource_type_id)
            logging.warn(action_types)
            for action_type in action_types:
                choices.append((action_type['id'], action_type['name']))
            self.fields['selected_action'].choices = choices
        except:
            logging.exception("Could not initialize form")
            exceptions.handle(request, ignore=False)
