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

from dragon.openstack.common import log as logging
from dragon.engine.clients import Clients

LOG = logging.getLogger(__name__)


class HeatTemplate(object):

    def __init__(self, context):
        self.clients = Clients(context)
        self.cntx = context
        self._instances = []
        self._volumes = []
        self._keypairs = []

    def add_instance(self, instance):
        self._instances.append(instance)

    def add_volume(self, volume):
        self._volumes.append(volume)

    def add_keypair(self, keypair):
        self._keypairs.append(keypair)

    def get_template(self):
        LOG.debug("heat_template :: get_template %s %s " %
                  (self._instances, self._volumes))
        raise NotImplementedError

    def process_recover_template(self, template_stream):
        self._mapper = []

    def get_instances(self):
        return self._instances

    def get_instance(self, name):
        for instance in self._instances:
            if instance.name == name:
                return instance

    def get_volumes(self):
        return self._volumes

    def get_volume(self, name):
        for volume in self._volumes:
            if volume.name == name:
                return volume


class TemplateResource(object):
    pass


class KeyPairResource(TemplateResource):

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name


class InstanceResource(TemplateResource):

    def __init__(self, image_snap_id, inst_name, flavor_name=None,
                 networks=None, security_groups=None,):
        self._snap_id = image_snap_id
        self._inst_name = inst_name
        self._flavor_name = flavor_name
        self._networks = networks
        self._security_groups = security_groups

    @property
    def image_snapshot_id(self):
        return self._snap_id

    @property
    def name(self):
        return self._inst_name

    @property
    def flavor_id(self):
        return self._flavor_name

    @property
    def networks(self):
        return self._networks

    @property
    def security_groups(self):
        return self._security_groups


class VolumeResource(TemplateResource):

    def __init__(self, name, id1, backup_id):
        self._name = name
        self._id = id1

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id


class HeatVolumeResource(VolumeResource):

    def __init__(self, name, id1, backup_id):
        super(self.__class__, self).__init__(name, id1)
        self._backup_id = backup_id

    @property
    def backup_id(self):
        return self._backup_id


class ParamVolumeResource(VolumeResource):
    def __init__(self, name, id1):
        super(self.__class__, self).__init__(name, id1)