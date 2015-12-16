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

""" Implementation of SQLAlchemy backend. """

from sqlalchemy.orm import joinedload
from dragon.common import crypt
from dragon.db.sqlalchemy import models
from dragon.db.sqlalchemy.session import get_session
from dragon.openstack.common import log as logging
LOG = logging.getLogger(__name__)


def model_query(context, *args):
    session = _session(context)
    query = session.query(*args)
    return query


def soft_delete_aware_query(context, *args, **kwargs):
    """Stack query helper that accounts for context's `show_deleted` field.

    :param show_deleted: if present, overrides context's show_deleted field.
    """

    query = model_query(context, *args)
    show_deleted = kwargs.get('show_deleted')

    if not show_deleted:
        query = query.filter_by(deleted_at=None)

    return query


def _session(context):
    return (context and context.session) or get_session()

"""
def policy_types_get_all(context):
    results = model_query(context, models.PolicyType).all()
    if not results:
        raise exception.NotFound('no policy types were found')
    return results
"""


def _encrypt(value):
    if value is not None:
        return crypt.encrypt(value.encode('utf-8'))


def _decrypt(enc_value):
    value = crypt.decrypt(enc_value)
    if value is not None:
        return unicode(value, 'utf-8')

"""  new dragon implementattion """

"""  resources   """

""" get all resources of given resource type """


def resources_get_by_type(context, tenant_id, resource_type):
    result = (model_query(context, models.Resources).
              filter_by(tenant_id=tenant_id).
              filter_by(resource_type_id=resource_type).all())

    return result


def resource_get(context, resource_id):

    LOG.warning(resource_id)
    result = (model_query(context, models.Resources).
              filter_by(id=resource_id).first())
    LOG.warning(result)
    return result


def resource_delete(context, resource_id):

    result = (model_query(context, models.Resources).
              filter_by(id=resource_id).first())

    result.delete()


def resource_get_all(context, tenant_id):
        LOG.debug("at resource_get_all  ++++")
        result = (model_query(context, models.Resources).
                  filter_by(tenant_id=tenant_id).all())

        return result


def resource_create(context, values):

    resource_ref = models.Resources()
    resource_ref.update(values)
    resource_ref.save(_session(context))
    return resource_ref

"""  resource_type   """


def resource_type_create(context, values):
    resource_type_ref = models.Resource_type()
    resource_type_ref.update(values)
    resource_type_ref.save(_session(context))
    return resource_type_ref


def resource_type_get(context, resource_type_id):
    result = (model_query(context, models.Resource_type).
              filter_by(id=resource_type_id).all())

    return result


def resource_type_update_action(context, resource_type_id):
    rt_ref = resource_type_get(context, resource_type_id)
    action_ref = action_get_by_resource_type(context, resource_type_id)

    if (action_ref is not None) and (rt_ref is not None):

        values = {'default_action_id': action_ref.id}
        rt_ref.update_and_save(values, session=None)
        return rt_ref
    else:
        return None


def resource_type_get_by_name(context, resource_type_name):
    result = (model_query(context, models.Resource_type).
              filter_by(name=resource_type_name).first())

    return result


def resource_type_get_all(context):
    LOG.debug(" at: resource_type_get_all +++  ")
    result = (model_query(context, models.Resource_type).all())

    return result

"""  actions """


def action_get_by_resource_type(context, resource_type_id):
    LOG.debug(" at: actions_get_by_resource +++ resource_type_id = %s "
              % resource_type_id)
    result = (model_query(context, models.Actions).
              filter_by(resource_type_id=resource_type_id).all())
#   LOG.debug("result = %s" % result[0]['name'])
    return result


def action_get_default_by_resource_type(context, resource_type_id):
    LOG.debug("at:action_get_default_by_resource_type+++resource_type_id = %s "
              % resource_type_id)
    resource_type = (model_query(context, models.Resource_type).
                     filter_by(id=resource_type_id).first())
    result = (model_query(context, models.Actions).
              filter_by(id=resource_type['default_action_id']).first())
    LOG.debug("result = %s" % result['name'])
    return result


def action_get(context, action_id):
    result = (model_query(context, models.Actions).
              filter_by(id=action_id).first())
    return result


def action_create(context, values):
    LOG.debug("at create_action : %s" % values)
    action_ref = models.Actions()
    action_ref.update(values)
    action_ref.save(_session(context))
    return action_ref


def action_delete(context, action_id):
    result = (model_query(context, models.Actions).
              filter_by(id=action_id).first())
    result.delete()

""" resource_actions """
""" get actions of a given resource  """


def resource_actions_get(context, workload_policy_id, resource_id):
    result = (model_query(context, models.Action_resource).
              options(joinedload('resource')).options(joinedload('action')).
              filter_by(resource_id=resource_id).
              filter_by(workload_policy_id=workload_policy_id).all())

    return result

# bring table with pointed resources and  actions


def resource_actions_get_by_workload(context, workload_policy_id):
    LOG.debug(" at: resource_actions_get_by_workload")
    result = (model_query(context, models.Action_resource).
              options(joinedload('resource')).options(joinedload('action')).
              filter_by(workload_policy_id=workload_policy_id).all())

    return result


def resource_actions_get_by_resource_id(context, resource_id):
    result = (model_query(context, models.Action_resource).
              options(joinedload('resource')).options(joinedload('action')).
              filter_by(resource_id=resource_id).all())

    return result


def resource_actions_create(context, values):
    action_resource_ref = models.Action_resource()
    action_resource_ref.update(values)
    action_resource_ref.save(_session(context))
    return action_resource_ref


def resource_actions_update(context, tuple_id, values):
    result = (model_query(context, models.Action_resource).
              filter_by(id=tuple_id))
    result.update(values)
    return result


def resource_actions_delete(context, tuple_id):
    LOG.debug("sqlalchemy/api: resource_actions_delete: %s"
              % (tuple_id))

    result = (model_query(context, models.Action_resource).
              filter_by(id=tuple_id).first())

    result.delete()


def resource_actions_delete_all_by_policy_id(context, workload_policy_id):
        results = (model_query(context, models.Action_resource).
                   filter_by(workload_policy_id=workload_policy_id).all())

        if results:
            for result in results:
                result.delete()

""" workload policy """


def workload_policy_create(context, values):
    workload_policy_ref = models.Workload_policies()
    workload_policy_ref.update(values)
    workload_policy_ref.save(_session(context))
    return workload_policy_ref


def workload_policy_delete(context, workload_policy_id):
    # db delete of child table entries
    workload_policy_execs =\
        workload_policy_excution_get_by_workload(context,
                                                 workload_policy_id)

    for workload_policy_exec in workload_policy_execs:
        id = workload_policy_exec['id']
        LOG.debug("workload_policy_delete/ workload_policy_exec_id %s "
                  % (id))
        action_excution_delete_all_by_policy_exec(context, id)
        workload_policy_execution_delete(context, id)

    resource_actions_delete_all_by_policy_id(context, workload_policy_id)

    result = (model_query(context, models.Workload_policies).
              filter_by(id=workload_policy_id).first())
    LOG.debug("workload_policy_delete/ workload_policy_id %s "
              % (workload_policy_id))
    LOG.debug("workload_policy_delete / delete result %s"
              % (result))

    # finally delete of workload_policy
    result.delete()


def workload_policy_get_all(context, tenant_id):
    LOG.debug("workload_policy_get_all . tenant_id = %s" % (tenant_id))
    result = (model_query(context, models.Workload_policies).
              filter_by(tenant_id=tenant_id).filter_by(deleted_at=None).all())

    return result


def workload_policy_get(context, workload_policy_id):
    result = (
        model_query(context, models.Workload_policies).
        filter_by(id=workload_policy_id).filter_by(deleted_at=None).first())

    return result

""" workload_policy_execution """


def workload_policy_excution_create(context, values):
    workload_policy_execution_ref = models.Workload_policy_execution()
    workload_policy_execution_ref.update(values)
    workload_policy_execution_ref.save(_session(context))

    return workload_policy_execution_ref


def workload_policy_excution_get_by_workload(context, workload_policy_id):
    result = (model_query(context, models.Workload_policy_execution).filter_by(
        workload_policy_id=workload_policy_id)).\
        order_by(models.Workload_policy_execution.created_at.desc()).\
        all()
    return result


def workload_policy_excution_get(context, policy_execution_id):
    result = (model_query(context, models.Workload_policy_execution).
              filter_by(id=policy_execution_id).all())

    return result


def workload_policy_execution_delete(context, workload_policy_exec_id):
    result = (model_query(context, models.Workload_policy_execution).
              filter_by(id=workload_policy_exec_id).first())

    if result:
        result.delete()


def workload_policy_execution_set_status(context,
                                         workload_policy_exec_id,
                                         policy_status):
    workload_policy_execution_ref =\
        (model_query(context,
                     models.Workload_policy_execution).
         filter_by(id=workload_policy_exec_id).first())

    value = {'status': policy_status}

    workload_policy_execution_ref.update(value)
    workload_policy_execution_ref.save(_session(context))

""" action execution """


def action_excution_create(context, values):
    action_execution_ref = models.Action_execution()
    action_execution_ref.update(values)
    action_execution_ref.save(_session(context))
    return action_execution_ref


def action_excution_update(context, workload_action_excution_id, resource_id,
                           action_id, values):
    result = (model_query(context, models.Action_execution).
              filter_by(id=workload_action_excution_id).
              filter_by(resource_id=resource_id).
              filter_by(action_id=action_id).all())

    result.update_and_save(values)    # just  update or also save ??


def action_excution_get_by_workload(context, policy_excution_id):
    result = (model_query(context, models.Action_execution).
              filter_by(workload_policy_execution_id=policy_excution_id).
              options(joinedload('resource')).options(joinedload('action')).
              order_by(models.Action_execution.created_at).all())

    return result


def action_excution_get(context, workload_action_excution_id,
                        resource_id, action_id):
    result = (model_query(context, models.Action_execution).
              filter_by(id=workload_action_excution_id).
              filter_by(resource_id=resource_id).
              filter_by(action_id=action_id).all())

    return result


def action_excution_delete_all_by_policy_exec(context,
                                              workload_policy_execution_id):
    results =\
        (model_query(context, models.Action_execution).filter_by
         (workload_policy_execution_id=workload_policy_execution_id).all())

    if results:
        for result in results:
            result.delete()
