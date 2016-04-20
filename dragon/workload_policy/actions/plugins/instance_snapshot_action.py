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

import StringIO
import os
import socket

from dragon.engine.clients import Clients
from dragon.openstack.common import log as logging
from dragon.openstack.common import exception
from dragon.workload_policy.actions import action
from dragon.workload_policy.actions import action_execution as ae
from oslo.config import cfg
import dragon.openstack.common.uuidutils as uuidutils
from eventlet import greenthread
from dragon.template.heat_template import InstanceResource

LOG = logging.getLogger(__name__)

instance_snapshot_opts = [
    cfg.IntOpt('backup_snapshot_object_size',
               default=52428800,
               help='The size in bytes of instance snapshots objects')
]

CONF = cfg.CONF
CONF.register_opts(instance_snapshot_opts)


class InstanceSnapshotAction(action.Action):
    is_global = False

    def __init__(self, context):
        self.clients = Clients(context)
        self._snap_id = None
        self._image_id = None
        self._name = None
        self._resource_id = None
        self.data_block_size_bytes = CONF.backup_snapshot_object_size
        # super(action.Action, self).__init__(workload_action_excution_id)

    def pre_protect(self, cntx, workload_action_excution_id,
                    resource_id):
        LOG.debug("pre protecting instance %s" % (resource_id))
        instance = self.clients.nova().servers.get(resource_id)
        # TODO(IBM): check instance state before pausing + passing original
        #               state to post_protect
        status = instance.pause()

        instance_snapshot_execution =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)
        instance_snapshot_execution.set_status(cntx, 'pausing VM')

    def post_protect(self, cntx, workload_action_excution_id,
                     resource_id):
        LOG.debug("post protecting instance %s" % (resource_id))
        instance = self.clients.nova().servers.get(resource_id)
        instance.unpause()
        instance_snapshot_execution =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)
        instance_snapshot_execution.set_status(cntx, 'un-pausing VM')

    def protect(self, cntx, workload_action_excution_id,
                resource_id, container_name):
        LOG.debug("protecting instance %s" % (resource_id))
        instance = self.clients.nova().servers.get(resource_id)
        self._image_id = instance.image['id']
        self._name = instance.name
        self._resource_id = resource_id
        instance_snapshot_exection =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)
        result = self._snapshot(cntx, instance, container_name,
                                instance_snapshot_exection)
        return result

    def generate_template(self, context, template_gen):
        instance = InstanceResource(self._image_id, self._name, resource_id=self._resource_id)
        template_gen.add_instance(instance)

    def failover(self, context, resource_id, resource_data, container_name):
        return self._import_from_swift(context, resource_id,
                                       resource_data, container_name)

    def _import_from_swift(self, context, resource_id,
                           resource_data, container_name):
        LOG.debug("resource %s data %s container %s" %
                  (resource_id, resource_data, container_name))
        swift_client = self.clients.swift()
        data_chunks = resource_data["chunks"]
        snap_id = resource_data["snap_id"]
        image_response_data = StringIO.StringIO()
        for chunk in range(data_chunks):
            swift_meta, image_response =\
                swift_client.get_object(container_name,
                                        snap_id + "_" + str(chunk))
            image_response_data.write(image_response)
        try:
            image = {}
            image['name'] = resource_data["meta"]["name"]
            image['size'] = resource_data["meta"]["size"]
            image['disk_format'] = resource_data["meta"]["disk_format"]
            image['container_format'] =\
                resource_data["meta"]["container_format"]
            image['id'] = uuidutils.generate_uuid()

            image_response_data.seek(0, os.SEEK_SET)
            self.clients.glance().images.create(data=image_response_data,
                                                **image)

            self._image_id = image['id']
            self._name = resource_data["instance_name"]
            return True
        # except ImageAlreadyPresentException:
        except Exception, e:
            LOG.error(e)
            return False

    def _snapshot(self, context, instance, container_name, action_excution):
        # metadata = instance.metadata
        n_client = self.clients.nova()
        snapshot_name = instance.name + "_snapshot"
        snapshot_metadata = instance.metadata

        instance_snapshot = instance.create_image(snapshot_name,
                                                  instance.metadata)
        self._snap_id = instance_snapshot
        action_excution.set_status(context, 'taking snapshot')
        local_snapshot = n_client.images.get(instance_snapshot)
        LOG.debug("checking instance snapshot %s %s "
                  % (local_snapshot.status, local_snapshot.progress))
        while (local_snapshot.status == "SAVING"):
            greenthread.sleep(1)
            local_snapshot = n_client.images.get(instance_snapshot)
        backup_rec = {}
        if local_snapshot.status == "ACTIVE":
            action_excution.set_status(context, 'uploading to swift')

            swift_conn = Clients(context).swift()
            headers = {'X-Container-Meta-dr_state': 'processing'}
            image = self.clients.glance().images.get(instance_snapshot)

            image_response = image.data()
            image_response_data = StringIO.StringIO()
            for chunk in image_response:
                image_response_data.write(chunk)
            image_response_data.seek(0, os.SEEK_SET)

            chunks = 0
            while True:
                data = image_response_data.read(self.data_block_size_bytes)
                data_offset = image_response_data.tell()
                LOG.debug("uploading offset %s chunks %s"
                          % (data_offset, chunks))
                if data == '':
                    break
                try:
                    swift_conn.put_object(container_name,
                                          instance_snapshot + "_" +
                                          str(chunks),
                                          data,
                                          content_length=len(data))
                    chunks += 1
                except socket.error as err:
                    raise exception.SwiftConnectionFailed(reason=str(err))

            dr_state = 'Protected'

            backup_rec["metadata"] = instance.metadata
            backup_rec["snap_id"] = self._snap_id
            backup_rec["instance_name"] = self._name
            backup_rec["meta"] = image.to_dict()
            backup_rec["chunks"] = chunks

            self._cleanup(context, n_client, self._snap_id)
        else:
            dr_state = 'DR clone backup failed'

        action_excution.set_status(context, dr_state)

        return dr_state, backup_rec

    def _cleanup(self, context, client, snapshot_id):
        client.images.delete(snapshot_id)
