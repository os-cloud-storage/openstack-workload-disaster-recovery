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



-- Resource type 
su db2inst1
db2 connect to dragon user dragon
db2 "insert into dragon.resource_type(created_at, updated_at, name, default_action_id) values ((VALUES current timestamp), (VALUES current timestamp), 'instance', NULL)"
db2 "insert into dragon.resource_type(created_at, updated_at, name, default_action_id) values ((VALUES current timestamp), (VALUES current timestamp), 'volume', NULL)"
db2 "insert into dragon.resource_type(created_at, updated_at, name, default_action_id) values ((VALUES current timestamp), (VALUES current timestamp), 'image', NULL)"

-- actions
db2 "insert into dragon.actions(created_at, updated_at, resource_type_id, class_name, name) values ( (VALUES current timestamp), (VALUES current timestamp), 2, 'dragon.workload_policy.actions.plugins.volume_snapshot_action.VolumeSnapshotAction', 'Volume Snapshot')"
db2 "insert into dragon.actions(created_at, updated_at, resource_type_id, class_name, name) values ( (VALUES current timestamp), (VALUES current timestamp), 1, 'dragon.workload_policy.actions.plugins.instance_snapshot_action.InstanceSnapshotAction', 'Image Snap')"

db2 "update dragon.resource_type set default_action_id=1 where name='volume'"
db2 "update dragon.resource_type set default_action_id=2 where name='instance'"
db2 "update dragon.resource_type set default_action_id=2 where name='image'"

commit
exit