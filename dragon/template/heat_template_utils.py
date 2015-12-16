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

from dragon.engine.clients import Clients
from dragon.openstack.common import log as logging

import yaml
import re
import traceback
import sys


LOG = logging.getLogger(__name__)


def generate_instance_and_net_section(context, snap, out):
    instance = snap['inst']
    image = snap['img']
    flavor = snap['flavor']
    ssh_key_name = snap['key_name']

    instance_name = instance.name
    image_name = image.name

    flavor_id = flavor.id
    fl = Clients(context).nova().flavors.get(flavor_id)
    flavor_name = fl.name

    instance_has_floating = False
    LOG.debug("instance networks %s" % snap['networks'])
    for net in snap['networks'].values():
        for address in net:
            LOG.debug("instance networks loop %s %s %s."
                      % (address, type(address), dir(address)))
            if address['OS-EXT-IPS:type'] == 'floating':
                instance_has_floating = True

    port_name = "%s_port" % instance_name

    if "resources" not in out or out["resources"] is None:
        out["resources"] = {}

    if ssh_key_name is not None:
        inst_properties = {
            "image": image_name,
            "flavor": flavor_name,
            "key_name": ssh_key_name,
            "networks": [{"port": {"get_resource": port_name}}],
        }
    else:
        inst_properties = {
            "image": image_name,
            "flavor": flavor_name,
            "networks": [{"port": {"get_resource": port_name}}],
        }

    out["resources"][instance_name] = {"type": "OS::Nova::Server",
                                       "properties": inst_properties
                                       }

    fixed_ips = []
    fixed_ips.append({'subnet_id': snap['remote_private_net_subnet_id']})
    out["resources"][port_name] = {
        "type": "OS::Neutron::Port",
        "properties": {
            "network_id": snap['remote_private_net_id'],
            "fixed_ips": fixed_ips,
        }
    }

    if instance_has_floating:
        floating_ip_name = "%s_floating_ip" % instance_name
        out["resources"][floating_ip_name] = {
            "type": "OS::Neutron::FloatingIP",
            "properties": {
                "floating_network_id": snap['remote_public_net_id'],
                "port_id": {"get_resource": port_name},
            }
        }

    LOG.debug("instance and net info = %s" % (out))


def generate_heat_template_volume_snapshot(context, snapshots):
    out = {}
    LOG.debug("_generate_heat_template_volume_snapshot")
    out["heat_template_version"] = "2013-05-23"
    for snap in snapshots:
        LOG.debug("_generate_heat_template_volume_snapshot %s" % (snap))
        instance = snap['inst']
        volumes = snap['volumes']
        instance_name = instance.name

        generate_instance_and_net_section(context, snap, out)

        if volumes:
            list_of_volumes = []
            for volume in volumes:
                out["resources"][volume['id']] = {
                    "type": "OS::Cinder::Volume",
                    "properties": {
                        "availability_zone": "nova",
                        "backup_id": volume['dr_backup_id']
                    }
                }

                volume_entry = {
                    "volume_id": {"Ref": volume['id']},
                    "device_name": volume['device']
                }
                list_of_volumes.append(volume_entry)
            bdm = 'block_device_mapping'
            out["resources"][instance_name]
            ["properties"][bdm] = list_of_volumes

    yaml_dumper = yaml.SafeDumper
    yml = yaml.dump(out, Dumper=yaml_dumper)
    # remove ordering from key names
    yml = re.sub('__\d*__order__', '', yml)
    return yml


def generate_heat_template_reverse_volume_snapshot(context, snapshots):
    out = {}
    LOG.debug("_generate_heat_template_reverse_volume_snapshot")
    out["heat_template_version"] = "2013-05-23"
    for snap in snapshots:
        LOG.debug("_generate_heat_template_reverse_volume_snapshot %s"
                  % (snap))
        instance = snap['inst']
        volumes = snap['volumes']
        instance_name = instance.name

        generate_instance_and_net_section(context, snap, out)

        if volumes:
            list_of_volumes = []
            for volume in volumes:
                consist_grp_name = ""
                if "consist_grp" in volume:
                    consist_grp_name = volume['consist_grp']
                volume_entry = {
                    "volume_id": {"Ref": volume['id']},
                    "device_name": volume['device']
                }
                out["resources"][volume['id']] = {
                    "type": "OS::Cinder::VolumeAttachment",
                    "properties": {
                        "volume_id": volume['id'],
                        "instance_uuid": {"get_resource": instance_name},
                        "mountpoint": volume['device'],
                        "consist_grp": consist_grp_name
                    }
                }
                list_of_volumes.append(volume_entry)
    yaml_dumper = yaml.SafeDumper
    yml = yaml.dump(out, Dumper=yaml_dumper)
    # remove ordering from key names
    yml = re.sub('__\d*__order__', '', yml)
    return yml


def heat_template_update_image_mapping(context, template, image_name,
                                       map_image_name):
    map1 = template["Mappings"]["ImageMap"]
    map_entry = {map_image_name: {"Map": map_image_name}}
    map1.update(map_entry)


def heat_template_update_vol_mapping(context, template, vol_id, map_vol_id):
    map1 = template["Mappings"]["VolMap"]
    map_entry = {vol_id: {"Map": map_vol_id}}
    map1.update(map_entry)


def heat_template_update_snapshot_mapping(context, template, snap_id,
                                          map_snap_id):
    map1 = template["Mappings"]["SnapMap"]
    map_entry = {snap_id: {"Map": map_snap_id}}
    map1.update(map_entry)


def heat_template_set_vol_snapshot(context, template, vol_id, snap_id):
    template["Resources"][vol_id]["Properties"]["SnapshotId"] = snap_id


def translate_attachment_detail_view(volume_id, instance_uuid, mountpoint):
    """Maps keys for attachment details view."""

    d = translate_attachment_summary_view(volume_id,
                                          instance_uuid,
                                          mountpoint)
    return d


def instance_volumes_list(context, instance):
        LOG.debug("_instance_volumes_list %s %s." % (instance, instance.id))
        bdms = Clients(context).nova().volumes.get_server_volumes(instance.id)

        if not bdms:
            LOG.debug(_("Instance %s is not attached."), instance.id)

        mountpoints = []

        for bdm in bdms:
            LOG.debug("bdm %s %s." % (bdm, dir(bdm)))
            volume_id = bdm.volumeId
            assigned_mountpoint = bdm.device
            if volume_id is not None:
                mountpoints.append(translate_attachment_detail_view(
                    volume_id,
                    instance.id,
                    assigned_mountpoint))

        return mountpoints


def translate_attachment_summary_view(volume_id, instance_uuid, mountpoint):
    """Maps keys for attachment summary view."""
    d = {}

    # NOTE(justinsb): We use the volume id as the id of the attachment object
    d['id'] = volume_id

    d['volumeId'] = volume_id

    d['serverId'] = instance_uuid
    if mountpoint:
        d['device'] = mountpoint

    return d


#  ssh keys: check at remote site
def is_remote_existing_keyname(dr_remote_nova_client, orig_ssh_key_name):
    all_key_names = [key.name for key in dr_remote_nova_client.keypairs.list()]
    if orig_ssh_key_name in all_key_names:
        return True
    else:
        return False


def instance_snapshot(context, instance):

    LOG.debug("In snapshot of instance %s ." % instance)
    try:
        image = Clients(context).glance().images.get(instance.image['id'])
        flavor = Clients(context).nova().flavors.get(instance.flavor['id'])

        key = Clients(context).nova().keypairs.get(instance.key_name)
        # returned object is keypair class
        LOG.debug("key_name type = %s" % type(key))

        ssh_key_name = remote_copy_ssh_key(context, key)
        LOG.debug("ssh key name (before write to snap)  = %s"
                  % (ssh_key_name))

        volumes = instance_volumes_list(context, instance)
        networks = Clients(context).remote_neutron().\
            list_networks()['networks']
        # ===================================================================
        LOG.debug("In snapshot, remote networks %s %s." %
                  (networks, dir(networks)))

        for net in networks:
            LOG.debug("In snapshot, network %s %s." % (net, dir(net)))
            if net['name'] == 'private':
                remote_private_net_id = net['id']
                remote_private_net_subnet_id = net['subnets'][0]
            if net['name'] == 'public':
                remote_public_net_id = net['id']

        LOG.debug("In remote private network id = %s."
                  % (remote_private_net_id))

        volume_mapping = []
        for v in volumes:
            LOG.debug("In snapshot, instance's volume %s %s." % (v, dir(v)))
            c_client = Clients(context).cinder()
            # cinder_client.cinderclient(context)
            vol = c_client.volumes.get(v['volumeId'])
            if ('dr_state' in vol.metadata and vol.
                    metadata['dr_state'] == "ready"):
                volume_mapping.append({
                    'id': v['volumeId'],
                    'device': v['device'],
                    'dr_backup_id': vol.metadata['dr_backup_id']})

        # ===================================================================
        # network_mapping = []
        # for net in networks:
        #  network = self.clients.nova().networks.get(net['id'])
        #  LOG.debug("In snapshot, instance's networks details %s ."
        #            % network)
        # ===================================================================

        return {'inst': instance,
                'img': image,
                'flavor': flavor,
                'key_name': ssh_key_name,
                'volumes': volume_mapping,
                'networks': instance.addresses,
                'remote_private_net_id': remote_private_net_id,
                'remote_private_net_subnet_id': remote_private_net_subnet_id,
                'remote_public_net_id': remote_public_net_id}
    except Exception, e:
            LOG.error("Failed getting master images %s" % (e))
            LOG.error(traceback.format_exc())
            LOG.error(sys.exc_info()[0])
            return None


# as part of the protect step
def remote_copy_ssh_key(context, key):

    LOG.debug(" key name =  %s" % (key))

    ssh_key_name = key.id
    # id is actually key name . see : novaclient/v1_1/keypairs.py/def id(self)
    LOG.debug("key name by dot =  %s" % (ssh_key_name))

    key_data = key.public_key
    LOG.debug("key data = %s." % (key_data))

    if ssh_key_name is not None:
        try:
            dr_remote_nova_client = Clients(context).remote_nova()

            LOG.debug('.... connected to remote Nova....')

            if (is_remote_existing_keyname(dr_remote_nova_client,
                                           ssh_key_name) is False):
                LOG.debug('....copying ssh key name : "%s"' % (ssh_key_name))

                dr_remote_nova_client.keypairs.create(ssh_key_name, key_data)
                LOG.debug('.... public key copied to remote Nova')

        except Exception:
            ssh_key_name = None
            LOG.error('write public key data to remote site/swift failed..')
    return ssh_key_name


def create_heat_snapshot(context):
    filters = {'deleted': False}
    instances = Clients(context).nova().servers.list(search_opts=filters)
    snapshot = []

    for instance in instances:
        LOG.debug(_("Creating heat snapshot, iterating instance %s ."),
                  instance.id)
        instance_id = instance.id
        metadata = Clients(context).nova().servers.get(instance_id).metadata
        if 'dr_state' in metadata and metadata['dr_state'] == "ready":
            snap = instance_snapshot(context, instance)
            snapshot.append(snap)

    return snapshot


def instance_snapshot_reverse_volume(context, instance):
    LOG.debug("In snapshot of instance %s ." % instance)
    try:
        image = Clients(context).glance().images.get(instance.image['id'])
        flavor = Clients(context).nova().flavors.get(instance.flavor['id'])
        volumes = instance_volumes_list(context, instance)
        networks = Clients(context).remote_neutron().\
            list_networks()['networks']
        # ===================================================================
        LOG.debug("In snapshot, remote networks %s %s."
                  % (networks, dir(networks)))

        for net in networks:
            LOG.debug("In snapshot, network %s %s." % (net, dir(net)))
            if net['name'] == 'private':
                remote_private_net_id = net['id']
                remote_private_net_subnet_id = net['subnets'][0]
            if net['name'] == 'public':
                remote_public_net_id = net['id']

        LOG.debug("In remote private network id = %s."
                  % (remote_private_net_id))

        volume_mapping = []
        for v in volumes:
            LOG.debug("In snapshot, instance's volume %s %s." % (v, dir(v)))
            c_client = Clients(context).cinder()
            vol = c_client.volumes.get(v['volumeId'])
            if (
                'dr_state' in vol.metadata and
                vol.metadata['dr_state'] == "ready"
            ):
                # check if the consistency group is present
                if vol.metadata['consist_grp_name']:
                    volume_mapping.append(
                        {'id': vol.metadata['dr_backup_id'],
                         'device': v['device'],
                         'consist_grp': vol.metadata['consist_grp_name']})
                else:
                    volume_mapping.append({'id': vol.metadata['dr_backup_id'],
                                           'device': v['device']})

        # ===================================================================
        # network_mapping = []
        # for net in networks:
        #  network = self.clients.nova().networks.get(net['id'])
        #  LOG.debug("In snapshot, instance's networks details %s." % network)
        # ===================================================================

        return {'inst': instance,
                'img': image,
                'flavor': flavor,
                'volumes': volume_mapping,
                'networks': instance.addresses,
                'remote_private_net_id': remote_private_net_id,
                'remote_private_net_subnet_id': remote_private_net_subnet_id,
                'remote_public_net_id': remote_public_net_id}
    except Exception, e:
            LOG.error("Failed getting master images %s" % (e))
            LOG.error(traceback.format_exc())
            LOG.error(sys.exc_info()[0])


def create_heat_snapshot_rev_vol(context):
    filters = {'deleted': False}
    instances = Clients(context).nova().servers.list(search_opts=filters)

    snapshot = []
    for instance in instances:
        LOG.debug(_("Creating heat snapshot, iterating instance %s ."),
                  instance.id)
        instance_id = instance.id
        metadata = Clients(context).nova().servers.get(instance_id).metadata
        # db.instance_metadata_get(context, instance_uuid)
        if 'dr_state' in metadata and metadata['dr_state'] == "ready":
            snap = instance_snapshot_reverse_volume(context, instance)
            snapshot.append(snap)

    return snapshot
