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

from dragon.engine.clients import Clients
from dragon.openstack.common import log as logging
from dragon.workload_policy.actions import action
from dragon.workload_policy.actions import action_execution as ae
from oslo.config import cfg
from eventlet import greenthread
from dragon.template.heat_template import HeatVolumeResource

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class VolumeSnapshotAction(action.Action):
    is_global = False

    def __init__(self, context):
        self.clients = Clients(context)
        self._name = None
        self._id = None
        self._backup_id = None
        self._resource_id = None
        # super(action.Action, self).__init__(workload_action_excution_id)

    def protect(self, cntx, workload_action_excution_id, resource_id,
                container_name):
        volume = self.clients.cinder().volumes.get(resource_id)

        self._name = volume.name
        self._id = volume.id
        self._resource_id = resource_id

        volume_snapshot_exection =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)
        result = self._replicate_volume_to_DR(cntx, volume, container_name,
                                              volume_snapshot_exection)
        return result

    def generate_template(self, context, template_gen):
        resource = HeatVolumeResource(self._name, self._id, self._backup_id)
        template_gen.add_volume(resource)

    def failover(self, context, resource_id, resource_data, container_name):
        return self._restore_volumes_from_swift(context, resource_id,
                                                resource_data,
                                                container_name)

    def _restore_volumes_from_swift(self, context, resource_id,
                                    resource_data, container_name):
        success = False

        cinder_client = self.clients.cinder()
        dr_backup = cinder_client.backups.import_record(
            resource_data['backup_service'],
            resource_data['backup_url'])
        dr_backup_id = dr_backup['id']
        temp_dr_backup = cinder_client.backups.get(dr_backup_id)
        LOG.debug("cinder backup status %s" % temp_dr_backup.status)
        while temp_dr_backup.status == "creating":
            greenthread.sleep(1)
            temp_dr_backup = cinder_client.backups.get(dr_backup_id)
        if temp_dr_backup.status == "available":
            # volume_snapshot_exection.set_status(context, 'ready')
            success = True

            LOG.debug("cinder backup status %s" % temp_dr_backup)

            self._name = temp_dr_backup.name
            self._id = temp_dr_backup.volume_id  # Remove this field!
            self._backup_id = dr_backup_id

        return success

    def _replicate_volume_to_DR(self, context, volume, container_name,
                                action_excution):
        metadata = volume.metadata
        c_client = self.clients.cinder()
        LOG.debug("cloning volume %s" % (volume.id))
        clone_volume = c_client.volumes.create(volume.size,
                                               source_volid=volume.id)
        clone_metadata = clone_volume.metadata
        action_excution.set_status(context, 'cloning')

        LOG.debug("clone_volume.id %s" % (clone_volume.id))
        temp_vol = c_client.volumes.get(clone_volume.id)
        #LOG.debug("temp_vol.status %s" % (temp_vol.status))

        backup_rec = None
        while (temp_vol.status == "creating"):
            greenthread.sleep(1)
            temp_vol = c_client.volumes.get(clone_volume.id)
            #LOG.debug("temp_vol.status %s" % (temp_vol.status))
        if temp_vol.status == "available":
            LOG.debug("creating backup %s" % (clone_volume.id))
            backup_store = c_client.backups.create(clone_volume.id,
                                                   container=container_name,
                                                   name=volume.name)
            action_excution.set_status(context, 'backup')
            temp_back = c_client.backups.get(backup_store.id)
            self._backup_id = backup_store.id
            #LOG.debug("temp_back.status %s" % (temp_back.status))
            while temp_back.status == "creating":
                greenthread.sleep(1)
                temp_back = c_client.backups.get(backup_store.id)
                #LOG.debug("temp_back.status %s" % (temp_back.status))
            if temp_back.status == "available":
                metadata['clone_backup_id'] = backup_store.id
                LOG.debug("exporting backup %s" % (backup_store.id))
                backup_rec = c_client.backups.export_record(backup_store.id)
                dr_state = "Protected"
                # TODO(Oshrit): Cleanup after exported to Swift
                # cleanup of bakcup record after export finished
                self._cleanup(context, c_client, clone_volume.id,
                              backup_store.id)
            else:
                dr_state = 'DR clone backup failed'
        else:
            dr_state = 'DR clone failed'

        action_excution.set_status(context, dr_state)
        LOG.debug("dr_state %s" % (dr_state))
        return dr_state, backup_rec

    def _cleanup(self, context, client, snapshot_id, backup_id):
        client.volumes.delete(snapshot_id)
        # client.backups.delete(backup_id)
