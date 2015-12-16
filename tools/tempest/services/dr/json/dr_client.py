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

import json
import re
import time
import urllib

from tempest_lib import exceptions as lib_exc

from tempest.common import service_client
from tempest import exceptions


class DRClient(service_client.ServiceClient):
        
    def list_workload_policies(self, params=None):
        """Lists all workload policies for a user."""
        uri = 'proj/list_workload_policies'
        if params:
            uri += '?%s' % urllib.urlencode(params)
            
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBodyList(resp, body['workload_policies'])
    
    def create_workload_policy(self, policy_name, tenant_id):
        post_body = {}
        post_body['name'] = policy_name        
        post_body['tenant_id'] = tenant_id
        # post_body = {'name': policy_name, 'tenant_id': tenant_id}
        body = json.dumps(post_body)
        # Password must be provided on stack create so that heat
        # can perform future operations on behalf of the user
        # headers = self.get_headers()
        # headers['X-Auth-Key'] = self.password
        # headers['X-Auth-User'] = self.user
        
        uri = 'create_workload_policy'
        resp, body = self.post(uri, headers=headers, body=body)
        self.expected_success(201, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)
        
    def get_workload_policy(self, workload_policy_id):
        """Returns the details of a single workload_policy."""
        url = "get_workload_policy/%s" % workload_policy_id
        resp, body = self.get(url)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body["workload_policy"])
    
    def list_resources(self):
        """Lists all resources."""
        uri = '%s/list_resources' % 'None'
            
        resp, body = self.get(uri)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)
    
    def create_resource(self, resource_id, resource_name,
                        resource_type_id, tenant_id):
        post_body = {}
        post_body['resource_id'] = resource_id        
        post_body['resource_name'] = resource_name
        post_body['resource_type_id'] = resource_type_id
        post_body['tenant_id'] = tenant_id
                        
        # post_body = {'name': policy_name, 'tenant_id': tenant_id}
        body = json.dumps(post_body)
        
        uri = '%s/create_resource' % 'None'
        resp, body = self.post(uri, headers=headers, body=body)
        self.expected_success(201, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)
        
    def get_resources(self, resource_id):
        """Returns the details of a single resource."""
        url = "%s/resource/%s" % ('None', resource_id)
        resp, body = self.get(url)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)

    def create_resource_action(self, resource_id, action_id, workload_policy_id):
        post_body = {}
        post_body['resource_id'] = resource_id        
        post_body['action_id'] = action_id
        post_body['workload_policy_id'] = workload_policy_id
                        
        # post_body = {'name': policy_name, 'tenant_id': tenant_id}
        body = json.dumps(post_body)
        
        uri = '%s/set_resource_action/%s' % ('None', resource_id)
        resp, body = self.post(uri, headers=headers, body=body)
        self.expected_success(201, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)

    def list_policy_executions(self, workload_policy_id):
        """Returns the details of a single resource."""
        url = "%s/list_policy_executions/%s" % ('None', workload_policy_id)
        resp, body = self.get(url)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)

    def get_policy_executions(self, policy_execution_id):
        url = "%s/get_policy_executions/%s" % ('None', policy_execution_id)
        resp, body = self.get(url)
        self.expected_success(200, resp.status)
        body = json.loads(body)
        return service_client.ResponseBody(resp, body)

    def protect(self, workload_identifier):
        """Protect a workload"""
        url = '%s/protect/%s' % ('None', workload_identifier)
        #body = {'workload_policy_id': workload_identifier}
        resp, body = self.post(url, json.dumps(body))
        self.expected_success(200, resp.status)
        return service_client.ResponseBody(resp, body)
    
    def recover(self, container_name):
        """Recover a workload"""
        url = '%s/recover' % 'None'
        body = {'container_name': container_name}
        resp, body = self.post(url, json.dumps(body))
        self.expected_success(200, resp.status)
        return service_client.ResponseBody(resp, body)
