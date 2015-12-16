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
        self.dr_networks = []
        self.credentials = {}
        self.dr_keynames = []
        self.context = context

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

        LOG.debug("heat_flame_template  input: image_snap_ids:  %s,"
                  "dr_volumes objects : %s dr_inst_names: %s dr_key_names %s "
                  % (self.dr_image_snapshot_ids, self.dr_volumes,
                     self.dr_protected_server_names, self.dr_keynames))

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

        generator = flame.TemplateGenerator(exclude_servers,
                                            False,
                                            exclude_networks,
                                            False,
                                            *arguments)

        LOG.debug("heat_flame_template : after flame.TemplateGenerator()")

        generator.run_no_print()  # 2 functions added to flame to avoid
        #  print the template. just keep it as dict
        template = generator.get_template()   # flame output

        LOG.debug("heat_flame_template  flame_template:  %s " % (template))

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
        to_del = []
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
                        if not vol_used:
                            to_del.append(item)

                        if vol_used:
                            self.dr_volumes.remove(vol_taken_out)

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
                del template['resources'][item]

        elif dr_used_heat_server_volumes != []:
            to_del = []
            for item in template['resources']:
                if item.startswith('volume_'):
                    if (item not in dr_used_heat_server_volumes):
                        to_del.append(item)

            for item in to_del:
                del template['resources'][item]

        else:  # but if no volumes are used or given at all in backed up
            # (dr) servers-> erase them all from the template
            for item in template['resources']:
                if item.startswith('volume_'):
                        to_del.append(item)

            for item in to_del:
                del template['resources'][item]

        # do not allow volumes in the parameters section
        to_del = []
        for item in template['parameters']:
            if item.startswith('volume_'):
                to_del.append(item)
        for item in to_del:
            del template['parameters'][item]

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
        floating ip
        first get rid of unused floatingip_association
        then get rid of unused floatingip
        """
        if self.dr_protected_server_names == []:
            # delete all floatingip_association_ and floatingip_ as there are no dr servers
            to_del = []
            for item in template['resources']:
                # this takes care of both floatingip_ and floatingip_association_
                if item.startswith('floatingip_'):
                        to_del.append(item)
            for item in to_del:
                del template['resources'][item]
        else:
            to_del = []
            dr_used_floating_ips = []
            for item in template['resources']:
                if item.startswith('floatingip_association_'):
                    server_key = template['resources'][item]['properties']['server_id']['get_resource']
                    if server_key not in template['resources']:
                        to_del.append(item)
                    else :
                        used_floatingip = template['resources'][item]['properties']['floating_ip']['get_resource']
                        dr_used_floating_ips.append(used_floatingip)
                        # also include item so it won't be deleted in for loop below
                        dr_used_floating_ips.append(item)
            
            for item in to_del:
                del template['resources'][item]

            to_del = []
            for item in template['resources']:
                # to do (KM): need to check the fields of form floatingip_nnn; don't delete fields beginning floatingip_association_
                if item.startswith('floatingip_'):
                    if item not in dr_used_floating_ips:
                        to_del.append(item)

            for item in to_del:
                del template['resources'][item]


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

        # key_names come  at recover time only. see: workload_policy.py
        # /failover()
        LOG.debug("dr_key_names %s " % (self.dr_keynames))

        for keypair in self._keypairs:
            self.dr_keynames.append(keypair.name)

        template = yaml.load(template_stream, Loader=yaml.SafeLoader)

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
