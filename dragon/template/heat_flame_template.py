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
from dragon.openstack.common import importutils
from dragon.template.heat_template import HeatTemplate
from dragon.engine.clients import Clients

from oslo.config import cfg

import flame
import yaml
import re
import copy

LOG = logging.getLogger(__name__)

template_opts = [
    cfg.BoolOpt('network_flat_mode',
                default=True,
                help='Default is  flat mode for Heat template servers'
                     '-avoid allocating networks parameters'),
]

cfg.CONF.register_opts(template_opts)


class HeatFlameTemplate(HeatTemplate):

    def __init__(self, context, is_unit_test=False):

        super(HeatFlameTemplate, self).__init__(context)
        self.dr_image_snapshot_ids = []
        self.dr_protected_server_names = []
        self.dr_volumes = []     # each has : volume name only !
        self.dr_replicated_volumes = []
        self.dr_networks = []
        self.credentials = {}
        self.dr_keynames = []
        self.context = context
        self.clients = Clients(context)
        LOG.debug("heat_flame_template  . initializing ")

        if is_unit_test is True:
            password = 'openstack1'
        else:
            importutils.import_module('keystoneclient.middleware.auth_token')
            password = cfg.CONF.keystone_authtoken.admin_password

        self.credentials = {'user': self.context.username,
                            'password': password,
                            'project': self.context.tenant,
                            'auth_url': self.context.auth_url,
                            'auth_token': self.context.auth_token}

        LOG.debug("heat_flame_template  credentials: user: %s, password : %s,"
                  "project: %s, auth_url %s , auth_token %s" %
                  (self.credentials['user'], self.credentials['password'],
                   self.credentials['project'], self.credentials['auth_url'],
                   self.credentials['auth_token']))

    def get_template(self):

        LOG.debug("heat_flame_template : begin get_template()")

        for inst in self._instances:
            self.dr_image_snapshot_ids.append(inst.image_snapshot_id)

        for inst in self._instances:
            self.dr_protected_server_names.append(inst.name)

        for vol in self._volumes:
            self.dr_volumes.append(vol)  # all the class

        for vol in self._replicated_volumes:
            self.dr_replicated_volumes.append(vol)

        LOG.debug("heat_flame_template  input: image_snap_ids:  %s,"
                  "dr_volumes objects : %s dr_inst_names: %s dr_key_names %s "
                  % (self.dr_image_snapshot_ids, self.dr_volumes,
                     self.dr_protected_server_names, self.dr_keynames))
        LOG.debug("heat_flame_template  input: dr_replicated_volumes:  %s," % (self.dr_replicated_volumes))

        insecure = False
        arguments = (self.credentials['user'], self.credentials['password'],
                     self.credentials['project'], self.credentials['auth_url'],
                     self.credentials['auth_token'], insecure)
        exclude_servers = False
        if self.dr_image_snapshot_ids == []:
            exclude_servers = True

        LOG.debug("network flat mode = %s " % (cfg.CONF['network_flat_mode']))
        network_flat_mode = cfg.CONF['network_flat_mode']
        if network_flat_mode is True:
            exclude_networks = True
        else:
            exclude_networks = False

        # temporary hack for debugging volumes; remove when running in ORBIT
        #exclude_networks = True
        generator = flame.TemplateGenerator(exclude_servers,
                                            False,
                                            exclude_networks,
                                            False,
                                            *arguments)

        LOG.debug("heat_flame_template : after flame.TemplateGenerator()")

        generator.run_no_print()  # 2 functions added to flame to avoid
        #  print the template. just keep it as dict
        template = generator.get_template()   # flame output

        LOG.debug("heat_flame_template  get_template:  %s " % (template))

        self.protect_post_process_template(template)

        yaml_dumper = yaml.SafeDumper
        yml = yaml.dump(template, Dumper=yaml_dumper)
        # remove ordering from key names
        yml_out = re.sub('__\d*__order__', '', yml)

        LOG.debug("heat_flame_template/get_template:  "
                  "yaml template output post process result:  %s"
                  % (yml_out))

        return yml_out

    def protect_post_process_template(self, template):
        """images."""
        LOG.debug("heat_flame_template  protect_post_process_template:  %s " % (template))
        to_del = []
        dr_used_heat_image_names = []
        if self.dr_image_snapshot_ids != []:
            for item in template['parameters']:
                if item.endswith('_image'):
                    if (
                        template['parameters'][item]['default'] not in
                        self.dr_image_snapshot_ids
                    ):
                        to_del.append(item)
                    else:
                        dr_used_heat_image_names.append(item)
            for item in to_del:
                del template['parameters'][item]

        else:
            for item in template['parameters']:
                if item.endswith('_image'):
                    to_del.append(item)

            for item in to_del:
                del template['parameters'][item]

        """servers."""
        to_del = []
        dr_used_heat_server_volumes = []
        dr_used_heat_server_replicated_volumes = []
        dr_used_heat_server_names = []

        LOG.debug("heat_flame_template:: dr_protected_server_names=  %s "
                  % (self.dr_protected_server_names))

        if self.dr_protected_server_names != []:
            LOG.debug("heat_flame_template:: dr_used_heatimage_names=  %s "
                      % (dr_used_heat_image_names))

            for item in template['resources']:
                if item.startswith('server_'):
                    t_prop = template['resources'][item]['properties']
                    is_in_heat = t_prop['image']['get_param'] in \
                        dr_used_heat_image_names
                    is_protected_server = t_prop['name'] in \
                        self.dr_protected_server_names
                    if (not is_in_heat or not is_protected_server):
                        to_del.append(item)
                    else:
                        dr_used_heat_server_names.append(item)

            for item in to_del:
                del template['resources'][item]

            for item in template['resources']:
                if item.startswith('server_'):
                    # look for volumes of above  servers
                    if ('block_device_mapping' in template['resources'][item]
                            ['properties']):
                        list_len = len(template['resources'][item]
                                       ['properties']['block_device_mapping'])
                        for index in range(0, list_len):
                            temp = template['resources'][item]['properties']
                            temp1 = temp['block_device_mapping'][index]
                            temp2 = temp1['volume_id']['get_resource']
                            vol_ref = temp2
#                           vol_ref = template['resources'][item]['properties']
#                           ['block_device_mapping'][index]['volume_id']
#                           ['get_resource']
                            dr_used_heat_server_volumes.append(vol_ref)

            LOG.debug("heat_flame_template:: dr_protected_server_names=  %s "
                      % (self.dr_protected_server_names))
            LOG.debug("heat_flame_template:: dr_used_heat_server_volumes= %s"
                      % (dr_used_heat_server_volumes))

        else:   # delete from heat template all servers if no image is used
            # or if only images given (no instance names ) we do nothing
            for item in template['resources']:
                if item.startswith('server_'):
                        to_del.append(item)
            for item in to_del:
                del template['resources'][item]

        """ volumes  """
        LOG.debug("heat_flame_template  template before fix volumes:  %s " % (template))
        to_del = []
        LOG.debug("heat_flame_template:: self.dr_volumes= %s" % (self.dr_volumes))
        if self.dr_volumes != []:
            for item in template['resources']:
                if item.startswith('volume_'):
                    t_prop = template['resources'][item]['properties']
                    if ('name' in t_prop):
                        vol_used = False
                        vol_taken_out = None
                        for dr_vol in self.dr_volumes:
                            if (t_prop['name'] == dr_vol.name):
                                vol_used = True
                                vol_taken_out = dr_vol
                                break
                        if vol_used:
                            self.dr_volumes.remove(vol_taken_out)
                            continue;

                        for dr_vol in self.dr_replicated_volumes:
                            if (t_prop['name'] == dr_vol.name):
                                vol_used = True
                                break
                        if not vol_used:
                            to_del.append(item)

                    elif ('source_volid' in template['resources'][item]
                          ['properties']):
                        if dr_used_heat_server_volumes != []:
                            # we have servers backed up  in this dr
                            if item not in dr_used_heat_server_volumes:
                                to_del.append(item)
                        else:
                            # for volumes backup only drop all those with no
                            # name
                            to_del.append(item)

            for item in to_del:
                LOG.debug("heat_flame_template:: item to delete = %s" % (item))
                del template['resources'][item]

        elif dr_used_heat_server_volumes != []:
            to_del = []
            for item in template['resources']:
                if item.startswith('volume_'):
                    if (item not in dr_used_heat_server_volumes):
                        to_del.append(item)

            for item in to_del:
                LOG.debug("heat_flame_template:: item to delete = %s" % (item))
                del template['resources'][item]

        else:  # but if no volumes are used or given at all in backed up
            # (dr) servers-> erase them all from the template
            for item in template['resources']:
                if item.startswith('volume_'):
                        to_del.append(item)

            for item in to_del:
                LOG.debug("heat_flame_template:: item to delete = %s" % (item))
                del template['resources'][item]

        # do not allow volumes in the parameters section
#         to_del = []
#         for item in template['parameters']:
#             if item.startswith('volume_'):
#                 to_del.append(item)
#         for item in to_del:
#             del template['parameters'][item]

        # fix entries that are replicated volumes
        LOG.debug("heat_flame_template  template before fix replicated volumes:  %s " % (template))
        to_del = []
        LOG.debug("heat_flame_template:: self.dr_replicated_volumes= %s" % (self.dr_replicated_volumes))
        if self.dr_replicated_volumes != [] :
            for item in template['resources']:
                if not item.startswith('volume_'):
                    continue
                LOG.debug("heat_flame_template:: item= %s" % (item))
                # check if this volume is replicated
                replicated_entry = False
                vol_used = False
                t_prop = template['resources'][item]['properties']
                LOG.debug("heat_flame_template:: props = %s" % (t_prop))
                if ('name' not in t_prop):
                    continue;
                for dr_vol in self.dr_replicated_volumes:
                    LOG.debug("heat_flame_template:: dr_vol.name = %s" % (dr_vol.name))
                    if (t_prop['name'] != dr_vol.name):
                        continue
                    replicated_entry = True
                    
                    # change from Cinder::Volume to Cinder::VolumeAttach
                    # find the server entry to which this volume belongs
                    for item2 in template['resources']:
                        if not item2.startswith('server_'):
                            continue
                        LOG.debug("heat_flame_template:: item2 = %s" % (item2))
                        server_props = template['resources'][item2]['properties']
                        if ('block_device_mapping' not in server_props):
                            continue
                        list_len = len(server_props['block_device_mapping'])
                        for index in range(0, list_len):
                            temp1 = server_props['block_device_mapping'][index]
                            LOG.debug("heat_flame_template:: temp1 = %s" % (temp1))
                            temp2 = temp1['volume_id']['get_resource']
                            LOG.debug("heat_flame_template:: item = %s, temp2 = %s" % (item, temp2))
                            if item != temp2 :
                                # no match
                                continue
                            mountpoint = temp1['device_name']
                            vol_used = True
                            break
                        if not vol_used :
                            continue
                        # fix server entry and volume entry
                        key_id = item + '_attachment_id'
                        key_name = item + '_attachment_name'
                        parameter = {
                            key_id: {
                                'type': 'string',
                                'description': 'id of attached volume',
                                'default': dr_vol.id
                            }
                        }
                        template['parameters'].update(parameter)
                        parameter = {
                            key_name: {
                                'type': 'string',
                                'description': 'name of attached volume',
                                'default': dr_vol.name
                            }
                        }
                        template['parameters'].update(parameter)
                        LOG.debug("heat_flame_template:: params = %s" % (template['parameters']))

                        template['resources'][item]['type'] = 'OS::Cinder::VolumeAttachment'
                        properties = {
                            'instance_uuid': {'get_resource' : item2 },
                            'volume_id' : {'get_param' : key_id },
                            'mountpoint' : mountpoint
                        }
                        template['resources'][item]['properties'] = properties
                        LOG.debug("heat_flame_template:: server_props before = %s" % (server_props))
                        del server_props['block_device_mapping'][index]
                        LOG.debug("heat_flame_template:: server_props after = %s" % (server_props))
                        # if block_device_mapping is now empty, remove the field completely
                        list_len = len(server_props['block_device_mapping'])
                        if list_len == 0 :
                            del server_props['block_device_mapping']
                        LOG.debug("heat_flame_template:: server_props after2 = %s" % (server_props))
                        break
                if replicated_entry and not vol_used:
                    to_del.append(item)
                                
            for item in to_del:
                LOG.debug("heat_flame_template:: item to delete = %s" % (item))
                del template['resources'][item]
        LOG.debug("heat_flame_template  template after fix volumes:  %s " % (template))

        """ keys """
        to_del = []
        if self.dr_protected_server_names == []:
            # delete all keys  since no servers
            for item in template['resources']:
                if item.startswith('key_'):
                    to_del.append(item)
            for item in to_del:
                del template['resources'][item]

        else:  # pick needed keys from dr (backed-up)   servers
            dr_used_key_names = []
            for itm in template['resources']:
                t_prop = template['resources'][itm]['properties']
                if itm.startswith('server_'):
                    is_key_exists = 'key_name' in t_prop
                    is_protected = \
                        t_prop['name'] in self.dr_protected_server_names
                    if (is_key_exists and is_protected):
                        key_name = t_prop['key_name']['get_resource']
#                       key_name = template['resources'][itm]['properties']
#                       ['key_name']['get_resource']
                        dr_used_key_names.append(key_name)

            LOG.debug("heat_flame_template:: dr_used_key_names=  %s "
                      % (dr_used_key_names))

            for item in template['resources']:
                if item.startswith('key_'):
                    if item not in dr_used_key_names:
                        to_del.append(item)

            for item in to_del:
                del template['resources'][item]

        """ security groups """
        to_del = []
        dr_used_heat_sec_groups = []
        if self.dr_protected_server_names != []:
            for item in template['resources']:
                if item.startswith('server_'):

                    if ('security_groups' in template['resources'][item]
                            ['properties']):
                        # serveral sec groups possible for single server
                        list_len = len(template['resources'][item]
                                       ['properties']['security_groups'])
                        for index in range(0, list_len):
                            dr_used_heat_sec_groups.append(
                                template['resources'][item]['properties']
                                ['security_groups'][index]['get_resource'])
            # go examine  all security groups
            to_del = []
            LOG.debug("heat_flame_template:: dr_used_heat_sec_groups=  %s "
                      % (dr_used_heat_sec_groups))

            for item in template['resources']:
                if item.startswith('security_group_'):
                    if item not in dr_used_heat_sec_groups:
                        to_del.append(item)

            for item in to_del:
                del template['resources'][item]

        else:  # delete all  security groups as there are no dr servers
            for item in template['resources']:
                if item.startswith('security_group_'):
                        to_del.append(item)
            for item in to_del:
                del template['resources'][item]

        """ flavors """
        to_del = []
        if self.dr_protected_server_names == []:
            # delete all from heat template if no server
            for item in template['parameters']:
                if item.endswith("_flavor"):
                    to_del.append(item)

            for item in to_del:
                    del template['parameters'][item]

        else:  # delete unused flavors
            to_del = []

            dr_used_heat_flavor_names = []

            dr_used_heat_server_names_copy = \
                copy.deepcopy(dr_used_heat_server_names)
            while True:
                try:
                    server_name = dr_used_heat_server_names_copy.pop()
                    flavor_name = server_name + '_flavor'
                    dr_used_heat_flavor_names.append(flavor_name)
                except:
                    break

            for item in template['parameters']:
                if item.endswith('_flavor'):
                    if item not in dr_used_heat_flavor_names:
                        to_del.append(item)

            for item in to_del:
                del template['parameters'][item]

        """
        floating ip handling
        in ORBIT, we need to reproduce the IP addresses on the secondary
        get rid of existing floatingip_association entries and re-create them.
        get rid of floatingip_ and external_network_for_floating_ip entries  
        create a port entry for the fixed ip address
        move the security groups info to the port entry
        """
        LOG.debug("heat_flame_template:: before floatingip handling template =  %s \n"
                      % (template))
        LOG.debug("heat_flame_template:: dr_protected_server_names=  %s \n"
                      % (self.dr_protected_server_names))
        to_del = []
        for item in template['resources']:
            # this takes care of both floatingip_ and floatingip_association_
            if item.startswith('floatingip_'):
                    to_del.append(item)
        for item in to_del:
            del template['resources'][item]

        to_del = []
        for item in template['parameters']:
            # this takes care of both floatingip_ and floatingip_association_
            if item.startswith('external_network_for_floating_ip_'):
                    to_del.append(item)
        for item in to_del:
            del template['parameters'][item]

        nova_client = self.clients.nova()
        new_resources = {}
        for item in template['resources']:
            if item.startswith('server_'):
                server_properties = template['resources'][item]['properties']
                server_name = server_properties['name']
                LOG.debug("server_name %s \n" % (server_name))
                # get the nova entry for this server (assuming names are unique)
                for inst in self._instances:
                    inst_name = inst.name
                    if inst_name is None:
                        continue
                    LOG.debug("inst_name %s \n" % (inst_name))
                    if inst_name == server_name:
                        vm_id = inst.resource_id
                        LOG.debug("vm_id %s \n" % (vm_id))
                        vm_details = nova_client.servers.get(vm_id)
                        #LOG.debug("image %s \n" % (str(vm_details.image)))
                        network_details = vm_details.networks
                        LOG.debug("network_details %s \n" % (network_details))
                        break
        
                if vm_details == None:
                    continue
                
                # To Do : assume for now that there is a single network; handle multiple networks
                # find the entries for the net and subnet
                # the template for server should already have a field of network field
                # remove the network field and replace it with a port field, since we want to replicate a specific IP address
                # move the security groups info from the server entry to the port entry
                if 'networks' not in server_properties :
                    continue
                network_list = server_properties['networks']
                LOG.debug("server_properties %s \n" % (server_properties))
                # the first (and only) element should be a network dictionary
                LOG.debug("network_list %s \n" % (network_list))
                network_dict = network_list[0]
                LOG.debug("network_dict %s \n" % (network_dict))
                if 'get_resource' not in network_dict['network']:
                    continue
                network_item = network_dict['network']['get_resource']
                LOG.debug("network_item %s \n" % (network_item))
                network_name = template['resources'][network_item]['properties']['name']
                LOG.debug("network_name %s \n" % (network_name))
                
                # find matching subnet field (assuming only one)
                subnet_item = None
                for item2 in template['resources']:
                    if item2.startswith('subnet_'):
                        subnet_properties = template['resources'][item2]['properties']
                        subnet_net_name = subnet_properties['network_id']['get_resource']
                        LOG.debug("subnet_net_name %s network_item %s \n" % (subnet_net_name, network_item))
                        if subnet_net_name == network_item:
                            subnet_item = item2
                            break
                LOG.debug("subnet_item %s \n" % (subnet_item))
                
                # using network name, extract info from vm_details
                if not network_name in network_details:
                    # error; break out
                    LOG.debug("network_name %s is not in network_details\n" % (network_name))
                    continue
                ip_addresses_list = network_details[network_name]
                list_len = len(ip_addresses_list)
                # first item is primary address - converted to port
                # additional items are floating IP associations
                # 'item' is name of resource (server_n)
                prefix, suffix = item.split('_')
                LOG.debug("prefix %s suffix %s \n" % (prefix, suffix))
                int_suffix = int(suffix)
                LOG.debug("int_suffix %d \n" % (int_suffix))
                port_resource_name = 'port_%d_0' % int_suffix
                LOG.debug("port_resource_name %s \n" % (port_resource_name))
                
                # move security groups from server entry to port entry
                security_groups = server_properties['security_groups']
                del server_properties['security_groups']

                # create port entry
                resource = {
                    port_resource_name: {
                        'type': 'OS::Neutron::Port',
                        'properties': {
                            'network': { 'get_resource': network_item },
                            'security_groups': security_groups,
                            'fixed_ips': [
                                ({
                                'subnet': {'get_resource': subnet_item},
                                'ip_address': ip_addresses_list[0]
                                })
                            ]
                        }
                    }
                }
                LOG.debug("resource %s \n" % (resource))
                new_resources.update(resource)
                
                # the remaining addresses are associated floating IPs
                for i in range(1, list_len):
                    # create an associated floating IP structure
                    fip_resource_name = 'floatingip_association_%d_%d' % (int_suffix, i)
                    fip_parameter_name1 = fip_resource_name + '_external_ip_address'
                    fip_parameter_name2 = fip_resource_name + '_external_ip_address_uuid'
                    LOG.debug("fip_resource_name %s \n" % (fip_resource_name))
                    resource = {
                        fip_resource_name: {
                            'type': 'OS::Neutron::FloatingIPAssociation',
                            'properties': {
                                'floatingip_id': {'get_param': fip_parameter_name2},
                                'port_id': { 'get_resource': port_resource_name }
                            }
                        }
                    }
                    LOG.debug("resource %s \n" % (resource))
                    new_resources.update(resource)
                    
                    # add the parameters for the associated floating IP addresses
                    parameter = {
                        fip_parameter_name1: {
                            'default': ip_addresses_list[i],
                            'description': 'floating IP to assign',
                            'type': 'string'
                        }
                    }
                    LOG.debug("parameter %s \n" % (parameter))
                    template['parameters'].update(parameter)
                    parameter = {
                        fip_parameter_name2: {
                            'default': 'to_be_plugged_on_secondary',
                            'description': 'uuid of floating IP to assign',
                            'type': 'string'
                        }
                    }
                    LOG.debug("parameter %s \n" % (parameter))
                    template['parameters'].update(parameter)

                # remove 'network' item from server properties and add 'port' item
                # accomplish this by overwriting the 'networks' field
                LOG.debug("server_properties %s \n" % (server_properties))
                server_properties['networks'] = [{'port': {'get_resource': port_resource_name}}]
                LOG.debug("server_properties %s \n" % (server_properties))

        LOG.debug("new_resources %s \n" % (new_resources))
        template['resources'].update(new_resources)
        LOG.debug("template = %s \n" % (template))
        
        # fix router entries
        # for ORBIT, the external network is called 'public' on both primary and secondary
        # To Do: Fix this hack
        to_del = []
        for item in template['resources']:
            if item.startswith('router_') and item.endswith('_gateway'):
                router_entry_name = item[:-8]
                LOG.debug("router_entry_name %s \n" % (router_entry_name))
                if not router_entry_name in template['resources']:
                    continue
                router_item_properties = template['resources'][router_entry_name]['properties']
                LOG.debug("router_item_properties %s \n" % (router_item_properties))
                gateway_properties = template['resources'][item]['properties']
                # change external network references to 'public'
                # instead of using network_id, use 'network' parameter
                net_id = gateway_properties['network_id']['get_param']
                LOG.debug("net_id %s \n" % (net_id))
                if not net_id.endswith('external_network'):
                    continue
                # delete the gateway entry; add gateway info to router entry
                # replace external gateway info with network:public
                router_item_properties['external_gateway_info'] = {'network': 'public'}
                LOG.debug("router_item_properties %s \n" % (router_item_properties))
                to_del.append(item)
        for item in to_del:
            LOG.debug("item to delete %s \n" % (item))
            del template['resources'][item]

        # remove from parameters those items that end with '_external_network' or router gateway
        to_del = []
        for item in template['parameters']:
            if item.endswith('_external_network'):
                LOG.debug("item to delete %s \n" % (item))
                to_del.append(item)
            if item.startswith('router_') and item.endswith('_gateway'):
                LOG.debug("item to delete %s \n" % (item))
                to_del.append(item)
        for item in to_del:
            del template['parameters'][item]

                        
        LOG.debug("heat_flame_template:: after floatingip handling template =  %s \n"
                      % (template))

        """ to do (KM): what about other new types of resources that may have been introduced? """


        """ reclean unused images: images referred by unused servers """
        if dr_used_heat_image_names == []:
            to_del = []

            dr_used_heat_server_names_copy = \
                copy.deepcopy(dr_used_heat_server_names)
            while True:
                try:
                    server_name = dr_used_heat_server_names_copy.pop()
                    image_name = server_name + '_image'
                    dr_used_heat_image_names.append(image_name)
                except:
                    break

            for item in template['parameters']:
                if item.endswith('_image'):
                    if item not in dr_used_heat_image_names:
                        to_del.append(item)

            for item in to_del:
                del template['parameters'][item]

    """ param template_stream is stream from  template.yaml i.e
         template_stream = open('template.yaml, 'r') """
    def process_recover_template(self, template_stream):
        LOG.debug("heat_flame_template/  start process_recover_template")

        if not (self._volumes != [] or self._instances != []):
            LOG.debug("heat_flame_template/process_recover : cannot recover."
                      " missing information to update Heat template")
            return

        super(HeatFlameTemplate, self).\
            process_recover_template(template_stream)

        for vol in self._volumes:
            self.dr_volumes.append(vol)

        for vol in self._replicated_volumes:
            self.dr_replicated_volumes.append(vol)

        # key_names come  at recover time only. see: workload_policy.py
        # /failover()
        LOG.debug("dr_key_names %s " % (self.dr_keynames))

        for keypair in self._keypairs:
            self.dr_keynames.append(keypair.name)

        template = yaml.load(template_stream, Loader=yaml.SafeLoader)
        LOG.debug("template before patching %s " % (template))

        """volumes - add  backup_id per each volume """
        if self.dr_volumes != []:
            for item in template['resources']:
                if item.startswith('volume_'):
                    detected_volume = None
                    for dr_vol in self.dr_volumes:
                        t_prop = template['resources'][item]['properties']
                        if 'name' in t_prop:
                            if (t_prop['name'] == dr_vol.name):
                                t_prop['backup_id'] = dr_vol.backup_id
                                detected_volume = dr_vol
                                break
                    if detected_volume:
                        self.dr_volumes.remove(detected_volume)
                        # defence : avoid provision of same volume name twice
                        # unless there are really 2 such with different
                        # backup_ids

        """ replicated volumes - add local volume id to parameters """
        if self.dr_replicated_volumes != [] : 
            LOG.debug("handling replicated volumes %s " % (self.dr_replicated_volumes))
            cinder_client = self.clients.cinder()
            volume_list = cinder_client.volumes.list()
            LOG.debug("volume_list %s " % (volume_list))
            for item in template['parameters']:
                if item.startswith('volume_') and item.endswith('_attachment_id'):
                    # get matching _attachment_name
                    param_name = item[0:-14] + '_attachment_name'
                    LOG.debug("param_name %s " % (param_name))
                    volume_name = template['parameters'][param_name]['default']
                    LOG.debug("volume_name %s " % (volume_name))
                    for cinder_item in volume_list :
                        if cinder_item.name == volume_name :
                            template['parameters'][item]['default'] = cinder_item.id
                            LOG.debug("updated item %s " % (template['parameters'][item]))
                            break;

        """ images - put new image_id of recover location instead of the
             protect time primary image_id"""
        if self._instances != []:
            server_image_ref_names = []
            inst_to_remove = None
            for item in template['resources']:
                if item.startswith('server_'):
                    for inst in self._instances:
                        inst_name = inst.name
                        if inst_name is None:
                            continue
                        image_id = inst.image_snapshot_id
                        if (template['resources'][item]['properties']
                                ['name'] == inst_name):
                            tup = (template['resources'][item]['properties']
                                   ['image']['get_param'], image_id)
                            if tup not in server_image_ref_names:
                                server_image_ref_names.append(tup)
                                inst_to_remove = inst
                            else:
                                inst_to_remove = None
                            break

                    if inst_to_remove:
                        self._instances.remove(inst_to_remove)
                        inst_to_remove = None

            # todo : if image not part of instances : scan self._instances
            # for orig img uuid vs new img uuid for replacement in the template
            # for that we need add to _instances  also orig_uuid  field
            if server_image_ref_names != []:
                image_namelist_len = len(server_image_ref_names)
                for item in template['parameters']:
                    if item.endswith('_image'):
                        for index in range(0, image_namelist_len):
                            image_name, image_id =\
                                server_image_ref_names[index]
                            if item == image_name:
                                template['parameters'][item]['default'] =\
                                    image_id
                                break

        # fix up uuid of floating IP address entries.
        # collect all the parameters to fix
        # then get a list of all the uuids
        # then plug the parameters
        params_to_fix = []
        for item in template['resources']:
            if item.startswith('floatingip_association_'):
                param = template['resources'][item]['properties'] \
                                   ['floatingip_id']['get_param']
                params_to_fix.append(param)
        LOG.debug("params_to_fix %s \n" % (params_to_fix))
        if params_to_fix != []:
            # get all the uuids
            neutronclient = self.clients.neutron()
            floatingip_entries = neutronclient.list_floatingips()
            for param in params_to_fix:
                LOG.debug("param %s \n" % (param))
                if not param.endswith('_external_ip_address_uuid'):
                    continue
                # obtain the matching ip address from the parameter list
                ip_var = param[:-5]
                ip_addr = template['parameters'][ip_var]['default']
                for floatingip in floatingip_entries['floatingips']:
                    if floatingip['floating_ip_address'] == ip_addr:
                        uuid = floatingip['id']
                        LOG.debug("uuid %s \n" % (uuid))
                        # plug the uuid value in the parameters section
                        template['parameters'][param]['default'] = uuid
                        break


        """   avoid data of keys that are already defined at the
              recover side """
        to_del = []
        if self.dr_keynames != []:  # list of local (recover site)key names

            for item in template['resources']:
                if item.startswith('key_'):
                    key_item = item
                    name = template['resources'][key_item]['properties']
                    ['name']
                    if name in self.dr_keynames:
                        to_del.append(key_item)
                        # look for servers that use this key name(key_item)
                        # and put there  just the name
                        for item in template['resources']:
                            if item.startswith('server_'):
                                # server_item = item
                                t_prop = \
                                    template['resources'][item]['properties']
                                if ('key_name' in t_prop):
                                    if (
                                        key_item ==
                                        t_prop['key_name']['get_resource']
                                    ):
                                        t_prop['key_name'] = name
            # cleanup
            for key_item in to_del:
                del template['resources'][key_item]

        LOG.debug("heat_flame_template/ recover  yaml template output of plant"
                  "image_id (before name change) and backup_id :  \n %s" %
                  (template))

        yaml_dumper = yaml.SafeDumper
        yml = yaml.dump(template, Dumper=yaml_dumper)
        # remove ordering from key names
        yml_out = re.sub('__\d*__order__', '', yml)

        LOG.debug("heat_flame_template/ recover  yaml template output of"
                  "plant image_id and backup_id :  \n %s" % (yml_out))

        return yml_out
