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

import platform

from dragon.engine.clients import Clients
from dragon.openstack.common import log as logging
from dragon.workload_policy.actions import action
from dragon.workload_policy.actions import action_execution as ae
from oslo.config import cfg
from eventlet import greenthread
from dragon.template.heat_template import VolumeResource

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class VolumeReplicationAction(action.Action):
    is_global = False

    def __init__(self, context):
        self.clients = Clients(context)
        self._name = None
        self._id = None

    def protect(self, context, workload_action_excution_id, resource_id,
                container_name):
        volume = self.clients.cinder().volumes.get(resource_id)

        self._name = volume.display_name
        self._id = volume.id

        volume_snapshot_exection =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)

        dr_state = "Protected"
        # TODO(IBM): should the dr_state reflect the drbd state? 
        # if yes - how do we validate drbd driver is alive and working?
        volume_snapshot_exection.set_status(context, dr_state)

        backup_rec = {}                
        backup_rec["metadata"] = volume.metadata
        backup_rec["volume_type"] = volume.volume_type
        backup_rec["volume_name"] = self._name
        return dr_state, backup_rec

    def generate_template(self, context, template_gen):
        resource = ParamVolumeResource(self._name, self._id)
        template_gen.add_volume(resource)

    def failover(self, context, resource_id, resource_data, container_name):
        #TODO(IBM): cleanup on failure 
        #TODO(IBM): Check volume_id does not already exist in the drbddriver code
        #TODO(IBM): drbd_manage can be constructed from CONF
        drbd_manage = platform.node() + "@" + resource_data["volume_type"] + "#drbdmanage"
        try:
            #  def manage(self, host, ref, name=None, description=None,
            #   volume_type=None, availability_zone=None, metadata=None,
            #   bootable=False):
            # cinder manage   --source-id 3956b0d7-010d-4eca-b45d-7a1d0bca9cae 
            #   --volume-type drbddriver-1  drbd0@drbddriver-1#drbdmanage
            ref_dict = {}
            ref_dict['source-name'] = resource_data["volume_name"]
            ref_dict['source-id'] = resource_id

            self.clients.cinder().volumes.manage(drbd_manage,
                                                 ref_dict,
                                                 name = resource_data["volume_name"],
                                                 volume_type = resource_data["volume_type"],
                                                 metadata = resource_data["metadata"])
            return True
        except Exception, e:
            LOG.error(e)
            return False

    def _cleanup(self, context, client, volume_id):
        pass
