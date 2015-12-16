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

from django.core.urlresolvers import reverse_lazy
from horizon import messages, tables
from openstack_dashboard.api import dragon
from openstack_dashboard.dashboards.project.draas_restore.tables import \
    DRRestoreBackupsTable, DRRestorePolicyExecutionTable
from openstack_dashboard.dashboards.project.volumes.tabs \
    import VolumeTableMixIn
from types import NoneType
import logging


LOG = logging.getLogger(__name__)


class IndexView(tables.MultiTableView, VolumeTableMixIn):
    table_classes = (DRRestoreBackupsTable,)
    template_name = 'project/draas_restore/index.html'
    success_url = reverse_lazy("horizon:project:draas_restore:index")

    def get_backups_data(self):
        try:
            dr_client = dragon.dragonclient(self.request)
            containers = dr_client.dr.recovery_list_policies()
            if type(containers) != NoneType:
                logging.info(containers)
                return containers
            else:
                return []
        except Exception, e:
            messages.error(self.request,
                           "cannot connect to recovery swift through dragon")
            logging.exception(e)
            return []


class RestorePolicyView(tables.MultiTableView):
    table_classes = (DRRestorePolicyExecutionTable,)
    template_name = 'project/draas_restore/policy_executions/index.html'

    def get_backups_data(self):
        try:
            dr_client = dragon.dragonclient(self.request)
            policy_name = self.kwargs['policy_name']
            containers = dr_client.dr \
                .recovery_list_policy_executions(policy_name)
            if type(containers) != NoneType:
                return containers
            else:
                return []
        except Exception, e:
            messages.error(self.request,
                    "cannot connect to recovery swift through dragon")
            logging.exception(e)
            return []
