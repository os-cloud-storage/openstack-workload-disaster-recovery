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

'''
Interface for database access.

The underlying driver is loaded . SQLAlchemy is currently the only
supported backend.
'''

from oslo.config import cfg

from dragon.db import utils

from dragon.openstack.common import log as logging
LOG = logging.getLogger(__name__)

SQL_CONNECTION = 'sqlite://'
SQL_IDLE_TIMEOUT = 3600
db_opts = [
    cfg.StrOpt('db_backend',
               default='sqlalchemy',
               help='The backend to use for db')]

cfg.CONF.register_opts(db_opts)

IMPL = utils.LazyPluggable('db_backend',
                           sqlalchemy='dragon.db.sqlalchemy.api')


cfg.CONF.import_opt('sql_connection', 'dragon.common.config')
cfg.CONF.import_opt('sql_idle_timeout', 'dragon.common.config')


def configure():
    global SQL_CONNECTION
    global SQL_IDLE_TIMEOUT
    SQL_CONNECTION = cfg.CONF.sql_connection
    SQL_IDLE_TIMEOUT = cfg.CONF.sql_idle_timeout


def get_session():
    return IMPL.get_session()

# =============================================================================
# Dragon Resources
# =============================================================================


def resources_get_by_type(context, tenant_id, resource_type):
    return IMPL.resources_get_by_type(context, tenant_id, resource_type)


def resource_delete(context, resource_id):
    return IMPL.resource_delete(context, resource_id)


def resource_actions_delete_all_by_policy_id(context, workload_policy_id):
    return IMPL.resource_actions_delete_all_by_policy_id(context,
                                                         workload_policy_id)


def resource_get(context, resource_id):
    return IMPL.resource_get(context, resource_id)


def resource_get_all(context, tenant_id):
    LOG.debug("get all resources ")
    return IMPL.resource_get_all(context, tenant_id)


def resource_create(context, values):
    return IMPL.resource_create(context, values)


def resource_type_create(context, values):
    return IMPL.resource_type_create(context, values)


def resource_type_get(context, resource_type_id):
    return IMPL.resource_type_get(context, resource_type_id)


def resource_type_get_by_name(context, resource_type_name):
    return IMPL.resource_type_get_by_name(context, resource_type_name)


def resource_type_get_all(context):
    return IMPL.resource_type_get_all(context)


def resource_type_update_action(context, resource_type_id):
    return IMPL.resource_type_update_action(context, resource_type_id)


def resource_type_delete(conetxt, resource_type):
    return IMPL.resource_type_delete(conetxt, resource_type)

# =============================================================================
# Dragon Actions
# =============================================================================


def action_get_by_resource_type(context, resource_type_id):
    LOG.debug("db.api rs_type_id = %s" % resource_type_id)
    return IMPL.action_get_by_resource_type(context, resource_type_id)


def action_get_default_by_resource_type(context, resource_type_id):
    LOG.debug("db.api rs_type_id = %s" % resource_type_id)
    return IMPL.action_get_default_by_resource_type(context, resource_type_id)


def action_get(context, action_id):
    return IMPL.action_get(context, action_id)


# The create and delete are admin operations invoked from the cli only
def action_create(context, values):
    return IMPL.action_create(context, values)


def action_delete(context, action_id):
    return IMPL.action_delete(context, action_id)


# Resource_action relationship, grouped in container to form a workload_policy

def resource_actions_get(context, workload_policy_id, resource_id):
    return IMPL.resource_actions_get(context, workload_policy_id, resource_id)


# join with action and resource
def resource_actions_get_by_workload(context, workload_policy_id):
    return IMPL.resource_actions_get_by_workload(context, workload_policy_id)


def resource_actions_create(context, values):
    return IMPL.resource_actions_create(context, values)


def resource_actions_update(context, tuple_id, values):
    return IMPL.resource_actions_update(context, tuple_id, values)


def resource_actions_delete(context, tuple_id):
    return IMPL.resource_actions_delete(context, tuple_id)


# Resource_action container
def workload_policy_create(context, values):
    return IMPL.workload_policy_create(context, values)


def workload_policy_delete(context, workload_policy_id):
    return IMPL.workload_policy_delete(context, workload_policy_id)


def workload_policy_get_all(context, tenant_id):
    return IMPL.workload_policy_get_all(context, tenant_id)


def workload_policy_get(context, workload_policy_id):
    return IMPL.workload_policy_get(context, workload_policy_id)

# =============================================================================
# Dragon Policy Executions
# =============================================================================


def workload_policy_excution_create(context, values):
    return IMPL.workload_policy_excution_create(context, values)


def workload_policy_excution_get_by_workload(context, workload_policy_id):
    return IMPL.workload_policy_excution_get_by_workload(context,
                                                         workload_policy_id)


def workload_policy_excution_get(context, policy_excution_id):
    return IMPL.workload_policy_excution_get(context, policy_excution_id)


def workload_policy_excution_actions_get(context, workload_policy_excution_id):
    return IMPL.action_excution_get_by_workload(context,
                                                workload_policy_excution_id)


def workload_policy_execution_set_status(context, workload_policy_exec_id,
                                         policy_status):
    return IMPL.workload_policy_execution_set_status(context,
                                                     workload_policy_exec_id,
                                                     policy_status)


def workload_policy_execution_delete(context, workload_policy_exec_id):
    return IMPL.workload_policy_execution_delete(context,
                                                 workload_policy_exec_id)

# =================================
# Dragon action excution  methods
# ==================================


def action_excution_create(context, values):
    return IMPL.action_excution_create(context, values)


def action_excution_update(context, workload_action_excution_id, resource_id,
                           action_id, values):
    return IMPL.action_excution_update(context, workload_action_excution_id,
                                       resource_id, action_id, values)


def action_excution_get_by_workload(context, workload_action_excution_id):
    return IMPL.action_excution_get_by_workload(context,
                                                workload_action_excution_id)


def action_excution_get(context, workload_action_excution_id,
                        resource_id, action_id):
    return IMPL.action_excution_get(context, workload_action_excution_id,
                                    resource_id, action_id)


def action_excution_delete_all_by_policy_exec(context,
                                              workload_policy_execution_id):
    return IMPL.action_excution_delete_all_by_policy_exec(
        context,
        workload_policy_execution_id)
