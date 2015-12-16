# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import routes

from dragon.api.openstack.v1 import dr
from dragon.common import wsgi
from dragon.openstack.common import log as logging

logger = logging.getLogger(__name__)


class API(wsgi.Router):

    """
    WSGI router for Heat v1 ReST API requests.
    """

    def __init__(self, conf, **local_conf):
        self.conf = conf
        mapper = routes.Mapper()

        dr_resource = dr.create_resource(conf)

        with mapper.submapper(controller=dr_resource,
                              path_prefix="/{project_id}") as dr_mapper:

            dr_mapper.connect('dr',
                              '/protect/{workload_policy_id}',
                              action='protect',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/recover',
                              action='recover',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/failback',
                              action='failback',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/resources',
                              action='list_resources',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/resources/{resource_id}',
                              action='get_resource',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/resource_types',
                              action='list_resource_types',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/resources',
                              action='create_resource',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/actions/{resource_type_id}',
                              action='list_actions',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/workload_policies',
                              action='create_workload_policy',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/workload_policies',
                              action='list_workload_policies',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/workload_policies/{workload_policy_id}',
                              action='get_workload_policy',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/workload_policies/{workload_policy_id}',
                              action='delete_workload_policy',
                              conditions={'method': ['DELETE']})

            dr_mapper.connect('dr',
                              '/get_default_action_for_resource_type/'
                              '{resource_type_id}',
                              action='get_default_action_for_resource_type',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/resource_action/{resource_id}',
                              action='set_resource_action',
                              conditions={'method': ['POST']})

            dr_mapper.connect('dr',
                              '/policy/{workload_policy_id}/resource/'
                              '{resource_id}/resource_action/{tuple_id}',
                              action='update_resource_action',
                              conditions={'method': ['PUT']})

            dr_mapper.connect('dr',
                              '/resource_action/{tuple_id}',
                              action='delete_resource_action',
                              conditions={'method': ['DELETE']})

            dr_mapper.connect('dr',
                              '/workload_policies/{workload_policy_id}/'
                              'resource_actions',
                              action='get_policy_resource_actions',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/workload_policies/{workload_policy_id}/'
                              'resources/{resource_id}/action',
                              action='get_policy_resource_action',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/workload_policies/{workload_policy_id}/'
                              'executions',
                              action='list_policy_executions',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/policy_executions/{policy_execution_id}',
                              action='get_policy_executions',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/policy_executions/{policy_execution_id}/'
                              'actions',
                              action='get_policy_execution_actions',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/recovery/policies',
                              action='recovery_list_policies',
                              conditions={'method': ['GET']})

            dr_mapper.connect('dr',
                              '/recovery/policies/{policy_name}/executions',
                              action='recovery_list_policy_executions',
                              conditions={'method': ['GET']})

        super(API, self).__init__(mapper)
