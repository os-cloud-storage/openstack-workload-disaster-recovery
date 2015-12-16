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

# from migrate.changeset import UniqueConstraint
# from migrate import ForeignKeyConstraint
# from sqlalchemy import Boolean, BigInteger, Enum, Float
# from sqlalchemy import dialects, Text, Index
# from sqlalchemy.types import NullType
from sqlalchemy import DateTime, Column
from sqlalchemy import ForeignKey, Integer, MetaData, String, Table
# from dragon.openstack.common import timeutils
import datetime
from dragon.openstack.common.gettextutils import _
from dragon.openstack.common import log as logging

LOG = logging.getLogger(__name__)


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    resource_type = Table('resource_type',
                          meta,
                          Column('id', Integer, primary_key=True,
                                 nullable=False),
                          # auto increment built in for Integer
                          Column('created_at', DateTime),
                          Column('updated_at', DateTime),
                          Column('name', String(length=50), nullable=False),
                          Column('default_action_id', Integer),
                          mysql_engine='InnoDB',
                          mysql_charset='utf8')

    actions = Table('actions', meta,
                    Column('id', Integer, primary_key=True, nullable=False),
                    Column('created_at', DateTime),
                    Column('updated_at', DateTime),
                    Column('deleted_at', DateTime),
                    Column('resource_type_id',
                           Integer, ForeignKey('resource_type.id'),
                           nullable=False),
                    Column('class_name', String(length=255), nullable=False),
                    Column('name', String(length=255)),
                    mysql_engine='InnoDB',
                    mysql_charset='utf8')

    resources = Table('resources', meta,
                      Column('id', String(length=255), primary_key=True,
                             nullable=False),
                      Column('created_at', DateTime),
                      Column('updated_at', DateTime),
                      Column('name', String(length=255), nullable=False),
                      Column('resource_type_id', Integer,
                             ForeignKey('resource_type.id'),
                             nullable=False),
                      Column('tenant_id', String(length=255), nullable=False),
                      mysql_engine='InnoDB',
                      mysql_charset='utf8')

    workload_policies = Table('workload_policies', meta,
                              Column('id', String(length=255),
                                     primary_key=True,
                                     nullable=False),
                              Column('created_at', DateTime),
                              Column('updated_at', DateTime),
                              Column('deleted_at', DateTime),
                              Column('name', String(length=255),
                                     nullable=False),
                              Column('tenant_id', String(length=255),
                                     nullable=False),
                              mysql_engine='InnoDB',
                              mysql_charset='utf8')

    workload_policy_execution = Table('workload_policy_execution', meta,
                                      Column('id', String(length=255),
                                             primary_key=True, nullable=False),
                                      Column('created_at', DateTime),
                                      Column('updated_at', DateTime),
                                      Column('workload_policy_id',
                                             String(length=255),
                                             ForeignKey('workload_policies.id',
                                                        ondelete="CASCADE"),
                                             nullable=False),
                                      Column('status', String(length=255),
                                             nullable=False),
                                      mysql_engine='InnoDB',
                                      mysql_charset='utf8')

    action_execution = Table('action_execution', meta,
                             Column('id', String(length=36),
                                    primary_key=True, nullable=False),
                             Column('created_at', DateTime),
                             Column('updated_at', DateTime),
                             Column('workload_policy_execution_id',
                                    String(length=36),
                                    ForeignKey('workload_policy_execution.id',
                                               ondelete="CASCADE"),
                                    nullable=False),
                             Column('action_id', Integer,
                                    ForeignKey('actions.id',
                                               ondelete="CASCADE"),
                                    nullable=False),
                             Column('status', String(length=255),
                                    nullable=False),
                             Column('resource_id', String(length=255),
                                    ForeignKey('resources.id'),
                                    nullable=False),
                             mysql_engine='InnoDB',
                             mysql_charset='utf8')

    action_resource = Table('action_resource', meta,
                            Column('id', Integer, primary_key=True,
                                   nullable=False),
                            Column('created_at', DateTime),
                            Column('updated_at', DateTime),
                            Column('deleted_at', DateTime),
                            Column('workload_policy_id', String(length=36),
                                   ForeignKey('workload_policies.id',
                                              ondelete="CASCADE"),
                                   nullable=False),
                            Column('resource_id', String(length=255),
                                   ForeignKey('resources.id'),
                                   nullable=False),
                            Column('action_id', Integer,
                                   ForeignKey('actions.id',
                                              ondelete="CASCADE"),
                                   nullable=False),
                            mysql_engine='InnoDB',
                            mysql_charset='utf8')

    tables = [resource_type, actions, resources, workload_policies,
              workload_policy_execution, action_execution, action_resource]

    for index, table in enumerate(tables):
        try:
            table.create()
        except Exception:
            for i in range(0, index):
                table[i].drop()
            LOG.exception(_('Exception while creating dragon db'
                            'table %s'), repr(table))

            raise

    _populate_resource_types(resource_type)
    _populate_actions(actions)


def downgrade(migrate_engine):

    meta = MetaData()
    meta.bind = migrate_engine

    action_resource = Table('action_resource', meta, autoload=True)
    action_execution = Table('action_execution', meta, autoload=True)
    workload_policy_execution = Table('workload_policy_execution',
                                      meta, autoload=True)
    workload_policies = Table('workload_policies', meta, autoload=True)
    resources = Table('resources', meta, autoload=True)
    actions = Table('actions', meta, autoload=True)
    resource_type = Table('resource_type', meta, autoload=True)

    tables = [action_resource, action_execution, workload_policy_execution,
              workload_policies, resources, actions, resource_type]

    for table in tables:
        try:
            table.drop()
        except Exception:
            LOG.exception(_('Exception while dropping table %s.'),
                          repr(table))
            raise


def _populate_resource_types(resource_type_table):
    default_resource_types = {
        'entry1': dict(name='instance', default_action_id=2,
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now())),
        'entry2': dict(name='volume', default_action_id=1,
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now())),
        'entry3': dict(name='image', default_action_id=3,
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now()))
    }

    try:
        i = resource_type_table.insert()
        type_names = sorted(default_resource_types.keys())
        for index in range(0, len(type_names)):
            values = default_resource_types[type_names[index]]
            i.execute({'name': values['name'],
                       'default_action_id': values['default_action_id'],
                       'created_at': values['created_at'],
                       'updated_at': values['updated_at']
                       })

    except Exception:
        LOG.info(repr(resource_type_table))
        LOG.exception(_('Exception while seeding resource_types table'))
        raise


def _populate_actions(actions_table):
    default_actions = {
        'entry1': dict(name='Volume Snapshot', resource_type_id=2,
                       class_name='dragon.workload_policy.actions.plugins.\
volume_snapshot_action.VolumeSnapshotAction',
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now())),
        'entry2': dict(name='Image Snapshot', resource_type_id=1,
                       class_name='dragon.workload_policy.actions.plugins.\
instance_snapshot_action.InstanceSnapshotAction',
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now())),
        'entry3': dict(name='Image Copy', resource_type_id=1,
                       class_name='dragon.workload_policy.actions.plugins.\
instance_image_action.InstanceImageAction',
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now())),
        'entry4': dict(name='Volume Replication', resource_type_id=2,
                       class_name='dragon.workload_policy.actions.plugins.\
volume_replication_action.VolumeReplicationAction',
                       created_at=str(datetime.datetime.now()),
                       updated_at=str(datetime.datetime.now()))                       

    }

    try:
        i = actions_table.insert()
        action_names = sorted(default_actions.keys())
        for index in range(0, len(action_names)):
            values = default_actions[action_names[index]]
            i.execute({'name': values['name'],
                       'resource_type_id': values['resource_type_id'],
                       'class_name': values['class_name'],
                       'created_at': values['created_at'],
                       'updated_at': values['updated_at']
                       })

    except Exception:
        LOG.info(repr(actions_table))
        LOG.exception(_('Exception while seeding actions table'))
        raise
