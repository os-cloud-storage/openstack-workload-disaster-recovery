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

import logging

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from horizon import tables
from openstack_dashboard import api
from horizon import messages

LOG = logging.getLogger(__name__)

DELETABLE_STATES = ("available", "error")


class RestorePolicyExecution(tables.Action):
    name = "restore_execution"
    verbose_name = _("Restore")
    classes = ("btn-create")

    def single(self, data_table, request, execution_name):
        try:
            dr_client = api.dragon.dragonclient(request)
            LOG.debug("dragon prepare parameters: %s " % (execution_name))
            dr_client.dr.recover(execution_name)
            messages.success(request,
                "Triggered restore of point in time: %s \n" % execution_name +
                " Check Heat deployment.")
        except Exception as e:
            logging.exception(e)
            messages.error(request, "Failed to trigger restore operation")


class SelectRestorePolicyAction(tables.LinkAction):
    name = "choose_policy"
    verbose_name = _("Select")
    url = "horizon:project:draas_restore:policy"
    classes = ("btn-launch")

    def get_link_url(self, datum):
        policy_name = datum['name']
        return reverse(self.url, kwargs={'policy_name': policy_name})


class DRRestoreBackupsTable(tables.DataTable):

    def get_object_id(self, container):
        return container['name']

    policy = tables.Column("name",
                         verbose_name=_("Policy Name"))
    timestamp = tables.Column("timestamp",
                         verbose_name=_("Last Run"))

    class Meta:
        name = "backups"
        verbose_name = _("Policies to Restore")
        status_columns = []
        row_actions = [SelectRestorePolicyAction]


class DRRestorePolicyExecutionTable(tables.DataTable):

    def get_object_id(self, container):
        return container['id']

    execution = tables.Column('name',
                         verbose_name=_("Policy"))
    timestamp = tables.Column('timestamp',
                         verbose_name=_("Timestamp"))

    class Meta:
        name = "backups"
        verbose_name = _("Points in Time")
        status_columns = []
        row_actions = [RestorePolicyExecution]
