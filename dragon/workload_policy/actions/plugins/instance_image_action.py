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
from dragon.template.heat_template import InstanceResource

LOG = logging.getLogger(__name__)

instance_image_opts = [
    cfg.IntOpt('backup_image_object_size',
               default=52428800,
               help='The size in bytes of instance image objects')
]

CONF = cfg.CONF
CONF.register_opts(instance_image_opts)


class InstanceImageAction(action.Action):

    is_global = True   # store in global container

    def __init__(self, context):
        self.clients = Clients(context)
        self._image_id = None
        self._name = None
        self._resource_id = None
        self.data_block_size_bytes = CONF.backup_image_object_size
        # super(action.Action, self).__init__(workload_action_excution_id)

    def pre_protect(self, cntx, workload_action_excution_id,
                    resource_id):
        pass

    def post_protect(self, cntx, workload_action_excution_id,
                     resource_id):
        pass

    def protect(self, cntx, workload_action_excution_id,
                resource_id, container_name):
        LOG.debug("protecting instance (image copied)  %s" % (resource_id))
        instance = self.clients.nova().servers.get(resource_id)
        self._image_id = instance.image['id']
        self._name = instance.name
        self._resource_id = resource_id

        instance_copy_execution =\
            ae.ActionExecution(workload_action_excution_id,
                               resource_id, self.id)
        result = self._imagecopy(cntx, instance, container_name,
                                 instance_copy_execution)
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
        image_id = resource_data["image_id"]
        image_response_data = StringIO.StringIO()
        for chunk in range(data_chunks):
            swift_meta, image_response =\
                swift_client.get_object(container_name,
                                        image_id + "_" + str(chunk))
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

    def _imagecopy(self, context, instance, container_name, action_excution):

        backup_rec = {}
        action_excution.set_status(context, 'uploaded to swift')
        swift_conn = Clients(context).swift()
        headers = {'X-Container-Meta-dr_state': 'processing'}
        image = self.clients.glance().images.get(self._image_id)

        # take the checksum as unique id
        global_container_image_id = image._info['checksum']
        image_response = image.data()
        image_response_data = StringIO.StringIO()
        for chunk in image_response:
            image_response_data.write(chunk)
        image_response_data.seek(0, os.SEEK_SET)

        chunks = 0
        while True:
            data = image_response_data.read(self.data_block_size_bytes)
            data_offset = image_response_data.tell()
            LOG.debug("uploading image offset %s chunks %s"
                      % (data_offset, chunks))
            if data == '':
                break
            try:
                swift_conn.put_object(container_name,
                                      global_container_image_id + "_" +
                                      str(chunks),
                                      data,
                                      content_length=len(data))
                chunks += 1
            except socket.error as err:
                dr_state = 'DR image backup failed'
                action_excution.set_status(context, dr_state)
                raise exception.SwiftConnectionFailed(reason=str(err))

        dr_state = 'Protected'

        backup_rec["metadata"] = instance.metadata
        backup_rec["image_id"] = global_container_image_id
        backup_rec["instance_name"] = self._name
        backup_rec["meta"] = image.to_dict()
        backup_rec["chunks"] = chunks

        action_excution.set_status(context, dr_state)
        return dr_state, backup_rec
