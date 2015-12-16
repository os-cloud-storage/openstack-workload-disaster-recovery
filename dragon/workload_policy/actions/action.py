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

from dragon.openstack.common import importutils
from dragon.openstack.common import log as logging
from dragon.common import exception
from dragon.workload_policy.actions import action_execution as ae

LOG = logging.getLogger(__name__)


class Action(object):

    def __init__(self):
        self.db_action = None
        self.id = None

    def _protect(self, cntx, workload_action_excution_id,
                 resource_id, container_name):
        return ae.ActionExecution(workload_action_excution_id,
                                  resource_id, self.id)

    def protect(self, cntx, workload_action_excution_id,
                resource_id, container_name):
        raise NotImplementedError

    def pre_protect(self, cntx, workload_action_excution_id,
                    resource_id):
        return True

    def post_protect(self, cntx, workload_action_excution_id,
                     resource_id):
        return True

    def generate_template(self, context):
        raise NotImplementedError

    def failover(self, context, resource_id, resource_data, container_name):
        raise NotImplementedError

    def _get_dr_volumes(self, clients):
        c_client = clients.cinder()
        volumes = c_client.volumes.list(detailed=True)
        LOG.debug("in _get_dr_volumes, retrieved volumes: %s" % (volumes))
        dr_volumes = [volume for volume in
                      volumes if 'dr_state' in volume.metadata]
        return dr_volumes

    def _extract_DR_Instances(self, clients, context):
        filters = {'deleted': False}
        metas = ['metadata', 'system_metadata']
        dr_instances = []
        instances = clients.nova().servers.list(search_opts=filters)
        LOG.debug("ExtractDRInstancesTask instances %s" % (instances))

        for db_inst in instances:
            LOG.debug("ExtractDRInstancesTask instance %s" % (db_inst))
            if 'dr_state' in db_inst.metadata:
                dr_instances.append(db_inst)
        return dr_instances

    @classmethod
    def is_using_global_container(cls):
        return cls.is_global


def load(from_obj, *args, **kwargs):
    # TODO(Oshrit): only from_obj.action needed
    LOG.debug("action load %s" % (from_obj.action.class_name))
    action_obj = load_action_driver(from_obj.action.class_name,
                                    *args, **kwargs)
    action_obj.db_action = from_obj
    action_obj.id = from_obj.action.id
    return action_obj


def load_action_driver(action_class, *args, **kwargs):
        """Load a compute driver module.
        :returns: a action instance
        """

        if not action_class:
            error = "action class not specified"

        LOG.debug(_("Loading action class '%s'") % action_class)
        try:
            action = importutils.import_object(action_class, *args, **kwargs)
            return action
        except ImportError:
            error = "Unable to load the action driver %s " % action_class

        LOG.exception(error)
        raise exception.ActionError(action=action_class)
