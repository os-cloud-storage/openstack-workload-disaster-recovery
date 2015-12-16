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

from .views import PoliciesView, AddPolicyView, PolicyView, EditActionView, \
    AddResourceView, PolicyExecutionView
from django.conf.urls import url
from django.conf.urls import patterns  # noqa

VIEW_MOD = 'openstack_dashboard.dashboards.project.draas.views'

urlpatterns = patterns('VIEW_MOD',
    url(r'^$', PoliciesView.as_view(), name='index'),
    url(r'^draas:new_policy$', AddPolicyView.as_view(), name='new_policy'),
    url(r'^policy/(?P<policy_id>[^/]+)$',
        PolicyView.as_view(), name='edit_policy'),
    url(r'^policy/(?P<policy_id>[^/]+)/add_resource_to_policy$',
        AddResourceView.as_view(),
        name='add_resource_to_policy'),
    url(r'^policy/(?P<policy_id>[^/]+)' +
        '/resource/(?P<resource_id>[^/]+)/edit_action/(?P<tuple_id>[^/]+)$',
        EditActionView.as_view(), name='edit_action'),
    url(r'^edit_action_post$', EditActionView.as_view(),
        name='edit_action_post'),
    url(r'^policy/(?P<policy_id>[^/]+)' +
        '/execution/(?P<policy_execution_id>[^/]+)$',
        PolicyExecutionView.as_view(), name='policy_execution'),
)
