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
SQLAlchemy models for Dragon data.
'''

import sqlalchemy

from sqlalchemy.dialects import mysql
from sqlalchemy.orm import relationship, backref, object_mapper
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import types
from json import dumps
from json import loads
from dragon.openstack.common import exception
from dragon.openstack.common import uuidutils
from dragon.openstack.common import timeutils
from dragon.db.sqlalchemy.session import get_session
from sqlalchemy.orm.session import Session
# from sqlalchemy import UniqueConstraint

BASE = declarative_base()


class Json(types.TypeDecorator):
    impl = types.Text

    def load_dialect_impl(self, dialect):
        if dialect.name == 'mysql':
            return dialect.type_descriptor(mysql.LONGTEXT())
        else:
            return self.impl

    def process_bind_param(self, value, dialect):
        return dumps(value)

    def process_result_value(self, value, dialect):
        return loads(value)

# TODO(leizhang) When we removed sqlalchemy 0.7 dependence
# we can import MutableDict directly and remove ./mutable.py
try:
    from sqlalchemy.ext.mutable import MutableDict as sa_MutableDict
    sa_MutableDict.associate_with(Json)
except ImportError:
    from dragon.db.sqlalchemy.mutable import MutableDict
    MutableDict.associate_with(Json)


class DragonBase(object):
    """Base class for Heat Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __table_initialized__ = False
    created_at = sqlalchemy.Column(sqlalchemy.DateTime,
                                   default=timeutils.utcnow)
    updated_at = sqlalchemy.Column(sqlalchemy.DateTime,
                                   onupdate=timeutils.utcnow)

    def save(self, session=None):
        """Save this object."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.add(self)
        try:
            session.flush()
        except IntegrityError as e:
            if str(e).endswith('is not unique'):
                raise exception.Duplicate(str(e))
            else:
                raise

    def expire(self, session=None, attrs=None):
        """Expire this object ()."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.expire(self, attrs)

    def refresh(self, session=None, attrs=None):
        """Refresh this object."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.refresh(self, attrs)

    def delete(self, session=None):
        """Delete this object."""
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.delete(self)
        session.flush()

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __iter__(self):
        self._i = iter(object_mapper(self).columns)
        return self

    def next(self):
        n = self._i.next().name
        return n, getattr(self, n)

    def update(self, values):
        """Make the model object behave like a dict."""
        for k, v in values.iteritems():
            setattr(self, k, v)

    def update_and_save(self, values, session=None):
        if not session:
            session = Session.object_session(self)
            if not session:
                session = get_session()
        session.begin()
        for k, v in values.iteritems():
            setattr(self, k, v)
        session.commit()

    def iteritems(self):
        """Make the model object behave like a dict.

        Includes attributes from joins.
        """
        local = dict(self)
        joined = dict([(k, v) for k, v in self.__dict__.iteritems()
                      if not k[0] == '_'])
        local.update(joined)
        return local.iteritems()


class SoftDelete(object):
    deleted_at = sqlalchemy.Column(sqlalchemy.DateTime)

    def soft_delete(self, session=None):
        """Mark this object as deleted."""
        self.update_and_save({'deleted_at': timeutils.utcnow()},
                             session=session)

"""   start dragon """


class Resource_type(BASE, DragonBase):

    __tablename__ = 'resource_type'

    id = sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True,
                           nullable=False, autoincrement=True)
    name = sqlalchemy.Column('name', sqlalchemy.String, nullable=False)

    default_action_id = sqlalchemy.Column(sqlalchemy.Integer,
                                          sqlalchemy.ForeignKey('actions.id'),
                                          nullable=True)


class Resources(BASE, DragonBase):

    __tablename__ = 'resources'

    id = sqlalchemy.Column('id', sqlalchemy.String,
                           primary_key=True,
                           default=uuidutils.generate_uuid)

    name = sqlalchemy.Column('name', sqlalchemy.String, nullable=False)
    tenant_id = sqlalchemy.Column('tenant_id', sqlalchemy.String,
                                  nullable=False)

    resource_type_id =\
        sqlalchemy.Column(sqlalchemy.Integer,
                          sqlalchemy.ForeignKey('resource_type.id'),
                          nullable=False)

    resource_type = relationship(Resource_type, lazy='joined',
                                 backref=backref('resources'),
                                 foreign_keys=resource_type_id,
                                 primaryjoin='Resources.resource_type_id=='
                                             'Resource_type.id')


class Actions(BASE, DragonBase):

        __tablename__ = 'actions'

        id = sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True,
                               nullable=False, autoincrement=True)
        class_name = sqlalchemy.Column('class_name', sqlalchemy.String,
                                       nullable=False)
        name = sqlalchemy.Column('name', sqlalchemy.String)

        resource_type_id =\
            sqlalchemy.Column(sqlalchemy.Integer,
                              sqlalchemy.ForeignKey('resource_type.id'))

        resource_type = relationship(Resource_type, backref=backref('actions'),
                                     foreign_keys=resource_type_id,
                                     primaryjoin='Actions.resource_type_id=='
                                                 'Resource_type.id')


class Workload_policies(BASE, DragonBase, SoftDelete):

    __tablename__ = 'workload_policies'

    id = sqlalchemy.Column('id', sqlalchemy.String,
                           primary_key=True,
                           default=uuidutils.generate_uuid)
    name = sqlalchemy.Column('name', sqlalchemy.String, nullable=False)
    tenant_id = sqlalchemy.Column('tenant_id',
                                  sqlalchemy.String, nullable=False)


class Workload_policy_execution(BASE, DragonBase):

    __tablename__ = 'workload_policy_execution'

    id = sqlalchemy.Column('id', sqlalchemy.String,
                           primary_key=True,
                           default=uuidutils.generate_uuid)

    status = sqlalchemy.Column('status', sqlalchemy.String, nullable=False)

    workload_policy_id =\
        sqlalchemy.Column(sqlalchemy.String,
                          sqlalchemy.ForeignKey('workload_policies.id'),
                          nullable=False)
    workload_policy =\
        relationship(Workload_policies,
                     backref=backref('workload_policy_execution'),
                     foreign_keys=workload_policy_id,
                     cascade="delete",
                     passive_deletes=True,
                     primaryjoin='Workload_policy_execution.'
                                 'workload_policy_id=='
                                 'Workload_policies.id')


class Action_execution(BASE, DragonBase):
        __tablename__ = 'action_execution'
        id = sqlalchemy.Column('id', sqlalchemy.String,
                               primary_key=True,
                               default=uuidutils.generate_uuid)

        status = sqlalchemy.Column('status', sqlalchemy.String,
                                   nullable=False)

        action_id = sqlalchemy.Column(sqlalchemy.Integer,
                                      sqlalchemy.ForeignKey('actions.id'),
                                      nullable=False)

        resource_id = sqlalchemy.Column(sqlalchemy.String,
                                        sqlalchemy.ForeignKey('resources.id'),
                                        nullable=False)

        workload_policy_execution_id = sqlalchemy.Column(
            sqlalchemy.String,
            sqlalchemy.ForeignKey('workload_policy_execution.id'),
            nullable=False)

        action =\
            relationship(Actions,
                         backref=backref('action_execution'),
                         foreign_keys=action_id,
                         primaryjoin='Action_execution.action_id==Actions.id')

        resource =\
            relationship(Resources,
                         backref=backref('action_execution'),
                         foreign_keys=resource_id,
                         primaryjoin='Action_execution.resource_id=='
                                     'Resources.id')

        workload_policy_exec =\
            relationship(Workload_policy_execution,
                         backref=backref('action_execution'),
                         foreign_keys=workload_policy_execution_id,
                         cascade="delete",
                         passive_deletes=True,
                         primaryjoin='Action_execution.'
                         'workload_policy_execution_id=='
                         'Workload_policy_execution.id')


class Action_resource(BASE, DragonBase):
            __tablename__ = 'action_resource'

            id = sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True,
                                   nullable=False, autoincrement=True)

            workload_policy_id = sqlalchemy.Column(
                sqlalchemy.String,
                sqlalchemy.ForeignKey('workload_policies.id'),
                nullable=False)

            resource_id =\
                sqlalchemy.Column(sqlalchemy.String,
                                  sqlalchemy.ForeignKey('resources.id'),
                                  nullable=False)

            action_id = sqlalchemy.Column(sqlalchemy.Integer,
                                          sqlalchemy.ForeignKey('actions.id'),
                                          nullable=False)

            resource =\
                relationship(Resources,
                             backref=backref('action_resource'),
                             foreign_keys=resource_id,
                             primaryjoin='Action_resource.resource_id=='
                                         'Resources.id')

            action =\
                relationship(Actions,
                             backref=backref('action_resource'),
                             foreign_keys=action_id,
                             primaryjoin='Action_resource.action_id=='
                                         'Actions.id')

            workload_policy =\
                relationship(Workload_policies,
                             backref=backref('action_resource'),
                             foreign_keys=workload_policy_id,
                             cascade="delete",
                             passive_deletes=True,
                             primaryjoin='Action_resource.'
                             'workload_policy_id== Workload_policies.id')
