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

import os
import time
from dragonclient import client as dr_client
from keystoneclient.v2_0 import client as ksclient
from novaclient.v1_1 import client as nova_client
from novaclient import shell as novashell
from cinderclient.v2 import client as cinder_client
from heatclient.v1 import client as heat_client

DR_INSTANCE = 1
DR_VOLUME = 2
INSTANCE_SNAPSOT_ACTION = 2
VOLUME_SNAPSHOT_ACTION = 1
IMAGE_COPY_ACTION = 3
DR_IMAGE_NAME = u'cirros-0.3.1-x86_64'
CIRROS_IMAGE_ID = u'52ab29ff-2069-4131-913c-73498ec6354c'
DR_VOL_NAME = "dr_vol1_test"
DR_POLICY_NAME = "system_test_policy"
DR_VM_NAME = "dr_vm1_test"
PROJECT_ID = u'72b0efd82b384b4880e4a8a0b163f0e5'


class SystemTestException(Exception):
    def __init__(self, message):
        self.message = message


class Dr_test(object):
    """Utility methods for running DR system test."""

    def __init__(self):
        args = {'auth_version': '2.0',
                'tenant_name': os.environ.get("OS_USERNAME"),  # "admin"
                'username': os.environ.get("OS_USERNAME"),  # "admin"
                'key': None,
                'auth_url': os.environ.get("OS_AUTH_URL"),
                'password': os.environ.get("OS_PASSWORD"), # "admin"
                'insecure': False,
                'timeout': 600,
                'cert_file': None,
                }
        ksclient = self._get_ksclient(**args)
        self.keystone = ksclient
        PROJECT_ID = ksclient.tenant_id
        endpoint = ksclient.service_catalog.url_for(service_type='dr',
                                                    endpoint_type='publicURL')
        args["token"] = ksclient.auth_token
        args["auth_token"] = args["token"]
        args["project"] = PROJECT_ID
        self.client = dr_client.Client("1", endpoint, **args)
        self.nova = self._get_nova(args["username"],
                                   args['password'],
                                   PROJECT_ID,
                                   os.environ.get("OS_AUTH_URL"),
                                   args["token"],
                                   False,
                                   ksclient)
        self.cinder = self._get_cinder(args["username"],
                                       args['password'],
                                       PROJECT_ID,
                                       os.environ.get("OS_AUTH_URL"),
                                       args["token"],
                                       False,
                                       ksclient)
        # self.context = context.get_admin_context()

    def _get_ksclient(self, **kwargs):
        """Get an endpoint and auth token from Keystone.

        :param username: name of user
        :param password: user's password
        :param tenant_id: unique identifier of tenant
        :param tenant_name: name of tenant
        :param auth_url: endpoint to authenticate against
        """
        return ksclient.Client(username=kwargs.get('username'),
                               password=kwargs.get('password'),
                               tenant_id=kwargs.get('tenant_id'),
                               tenant_name=kwargs.get('tenant_name'),
                               auth_url=kwargs.get('auth_url'),
                               insecure=kwargs.get('insecure'))

    def _get_nova(self, username, password, project, auth_url,
                 auth_token, insecure, keystone):
        computeshell = novashell.OpenStackComputeShell()
        extensions = computeshell._discover_extensions("1.1")

        args = {
            'project_id': project,
            'auth_url': auth_url,
            'service_type': 'compute',
            'username': None,
            'api_key': None,
            'extensions': extensions,
            'insecure': insecure
        }

        nova = nova_client.Client(**args)
        management_url =\
            keystone.service_catalog.url_for(service_type='compute',
                                             endpoint_type='publicURL')
        nova.client.auth_token = auth_token
        nova.client.management_url = management_url
        return nova

    def _get_cinder(self, username, password, project, auth_url,
                 auth_token, insecure, keystone):
        args = {
            'auth_url': auth_url,
            'project_id': project,
            'tenant_id': project,
            'username': username,
            'insecure': insecure,
            'api_key': None
        }

        cinder = cinder_client.Client(**args)
        management_url =\
            keystone.service_catalog.url_for(service_type='volumev2',
                                             endpoint_type='publicURL')
        cinder.client.auth_token = auth_token
        cinder.client.management_url = management_url
        return cinder

    def _get_heat(self, username, password, project, auth_url,
                 auth_token, insecure, keystone):
        kwargs = {
                  'insecure': False,
                  'ca_file': None,
                  'username': username,
                  'insecure': insecure,
                  'auth_url': auth_url,
                  'tenant_id': project,
                  'token':auth_token
                  }

        heat = heat_client.Client(keystone.service_catalog.url_for(service_type='orchestration',
                                                                   endpoint_type='publicURL'),
                                  **kwargs)
        management_url = keystone.service_catalog.url_for(service_type='orchestration',
                                                          endpoint_type='publicURL')
        # heat.client.auth_token = auth_token
        # cinder.client.management_url = management_url

        return heat

    def sanity_check(self):
        instance_actions = self.client.dr.list_actions(DR_INSTANCE)
        volume_actions = self.client.dr.list_actions(DR_VOLUME)
        is_instance = (len(instance_actions) == 2 and
                       instance_actions[0]["class_name"] == 'dragon.workload_policy.actions.plugins.instance_snapshot_action.InstanceSnapshotAction' and
                       instance_actions[1]["class_name"] == 'dragon.workload_policy.actions.plugins.instance_image_action.InstanceImageAction')
        is_volume = (len(volume_actions) == 1 and
                     volume_actions[0]["class_name"] == 'dragon.workload_policy.actions.plugins.volume_snapshot_action.VolumeSnapshotAction')
        return is_instance and is_volume

    def get_image_by_name(self, image_name):
        for image in self.nova.images.list():
            if (image.name == image_name):
                return image.id
        return CIRROS_IMAGE_ID

    def create_dr_instance(self, new_vm_name, image_name):
        nova_networks = self.nova.networks.list()
        if (nova_networks is not None):
            nic = {}
            nic["net-id"] = nova_networks[0].id
            dr_vm1_test = self.nova.servers.create(flavor=1, image=image_name, name=new_vm_name, nics=[nic])
        else:
            dr_vm1_test = self.nova.servers.create(flavor=1, image=image_name, name=new_vm_name)
        while (dr_vm1_test.status not in ("ACTIVE", "ERROR")):
            time.sleep(2)
            dr_vm1_test = self.nova.servers.get(dr_vm1_test.id)
        if (dr_vm1_test.status == "ACTIVE"):
            self.client.dr.create_resource(dr_vm1_test.id, new_vm_name, DR_INSTANCE)
            return dr_vm1_test.id
        else:
            return None

    def create_dr_volume(self, name):
        dr_vol1_test = self.cinder.volumes.create(size=1, name=name)
        while (dr_vol1_test.status not in ("available", "error")):
                time.sleep(2)
                dr_vol1_test = self.cinder.volumes.get(dr_vol1_test.id)
        if (dr_vol1_test.status == "available"):
            self.client.dr.create_resource(dr_vol1_test.id, name, DR_VOLUME)
            return dr_vol1_test.id
        else:
            return None

    def attach_volume(self, vm_id, vol_id):
        self.nova.volumes.create_server_volume(vm_id, vol_id, "/dev/vdb")
        dr_vol1_test = self.cinder.volumes.get(vol_id)
        while (dr_vol1_test.status == "attaching"):
            time.sleep(2)
            dr_vol1_test = self.cinder.volumes.get(vol_id)

    def create_workload_policy(self, policy_name):
        workload_policy = self.client.dr.create_workload_policy(policy_name, PROJECT_ID)
        return workload_policy["id"]

    def add_resource_to_workload(self, resource, action_id, workload_id):
        self.client.dr.create_resource_action(resource, action_id, workload_id)

    def protect(self, workload_id):
        self.client.dr.protect(workload_id)
        time.sleep(15)
        policy_executions = self.client.dr.list_policy_executions(workload_id)
        policy_execution_id =  policy_executions[0]["id"]
        policy_execution = self.client.dr.get_policy_executions(policy_execution_id)
        while (policy_execution[0]["status"] not in ("Protected", "Error")):
                time.sleep(2)
                policy_execution =\
                    self.client.dr.get_policy_executions(policy_execution_id)
        return (policy_execution[0]["status"] == "Protected")

    def recover_by_policy_name(self, policy):
        container_name = self.client.dr.recovery_list_policy_executions(DR_POLICY_NAME)[0]["id"]
        self.client.dr.recover(container_name)
        return container_name

    def check_heat_stack(self, stack_name):
        heat = self._get_heat(os.environ.get("OS_USERNAME"),
                              os.environ.get("OS_PASSWORD"),
                              PROJECT_ID,
                              os.environ.get("OS_AUTH_URL"),
                              self.keystone.auth_token,
                              False,
                              self.keystone)
        stack = heat.stacks.get(stack_name)
        while (stack.stack_status == "CREATE_IN_PROGRESS"):
            time.sleep(5)
            stack = heat.stacks.get(stack_name)
        return (stack.stack_status == "CREATE_COMPLETE")

    def is_instance_exists(self, instance_name):
        servers = self.nova.servers.list()
        for server in servers:
            if server.name == instance_name:
                return True
        return False

    def is_volume_exists(self, volume_name):
        vols = self.cinder.volumes.list()
        for vol in vols:
            if vol.name == volume_name:
                return True
        return False

    def cleanup(self, vm_id, vol_id, workload_id):
        try:
            if (vm_id is not None):
                try:
                    self.nova.volumes.delete_server_volume(vm_id, vol_id)
                except Exception, ex:
                    pass
                time.sleep(2)
                self.nova.servers.delete(vm_id)
                time.sleep(2)
            if (vol_id is not None):
                self.cinder.volumes.delete(vol_id)
            if (workload_id is not None):
                self.client.dr.delete_workload_policy(workload_id)
        except Exception, e:
            print e
        
    def cleanup_stack(self, stack_name):
        heat = self._get_heat(os.environ.get("OS_USERNAME"),
                              os.environ.get("OS_PASSWORD"),
                              PROJECT_ID,
                              os.environ.get("OS_AUTH_URL"),
                              self.keystone.auth_token,
                              False,
                              self.keystone)
        stack = heat.stacks.get(stack_name)
        print "Deleting stack %s" % stack_name
        heat.stacks.delete(stack_name)


""" System test starts here:
1. Create VM
2. Create Volume
3. Attach volume to VM
4. Mark the VM and volume for DR
5. Create DR workload policy
6. Add the resouces to the workload policy with Snapshots actions
7. Protect the workload policy
8. Recover the workload policy
9. Check stack creation was successful
 """
test = Dr_test()
try:
    dr_vm_id = None
    dr_vol_id = None
    workload_policy_id = None

    if (test.sanity_check()):
        print "DR sanity check OK"
    else:
        print "DR installation error - actions are not defined properly"
    image_id = test.get_image_by_name(DR_IMAGE_NAME)
    dr_vm_id = test.create_dr_instance(DR_VM_NAME, image_id)
    if (dr_vm_id is None):
        print "create_dr_instance FAIL"
    else:
        print "DR instance created OK"
    dr_vol_id = test.create_dr_volume(DR_VOL_NAME)
    if (dr_vol_id is None):
        print "create_dr_volume FAIL"
    else:
        print "DR volume created OK"
    test.attach_volume(dr_vm_id, dr_vol_id)
    print "Volume was attached OK"
    workload_policy_id = test.create_workload_policy(DR_POLICY_NAME)
    if (workload_policy_id is not None):
        print "DR workload policy created OK"
    test.add_resource_to_workload(dr_vm_id,
                                  INSTANCE_SNAPSOT_ACTION,
                                  workload_policy_id)
    print ("DR resource was added to workload policy OK")
    test.add_resource_to_workload(dr_vol_id,
                                  VOLUME_SNAPSHOT_ACTION,
                                  workload_policy_id)
    print ("DR resource was added to workload policy OK")
    if (not test.protect(workload_policy_id)):
        print "Error protecting workload"
        raise SystemTestException("Error protecting workload")
    else:
        print "DR workload protected OK"
    time.sleep(200)

    container_name = test.recover_by_policy_name(DR_POLICY_NAME)
    print "DR workload recovered OK"

    # Verify Heat stack created OK
    time.sleep(10)
    if (test.check_heat_stack(container_name)):
        print "DR stack check OK"
        
    # Delete original resources
    test.cleanup(dr_vm_id, dr_vol_id, None)

    # Check recovered resources exists
    if test.is_instance_exists(DR_VM_NAME):
        print "instance recovred OK"
    else:
        print "instance recovered FAIL"

    if test.is_volume_exists(DR_VOL_NAME):
        print "volume recovered OK"
    else:
        print "volume recovered FAIL"

    # Delete stack - will delete recovered resources
    test.cleanup_stack(container_name)
except Exception, e:
    print e
    test.cleanup(dr_vm_id, dr_vol_id, None)
    raise SystemTestException(e)
