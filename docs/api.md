Dragon OpenStack API Reference
============================

List resource types
---------------

GET /v1/{project_id}/resource_types

Result:

```
HTTP/1.1 200 OK
[{Resource type 1}, {Resource type 2}]

[{ "resource_type": {"name": "instance", "created_at": "2015-02-17T18:50:09.629273", "updated_at": "2015-02-17T18:50:09.629316", "default_action_id": 2, "id": 1}},
 { "resource_type": {"name": "volume", "created_at": "2015-02-17T18:50:09.629273", "updated_at": "2015-02-17T18:50:09.629316", "default_action_id": 1, "id": 2}}] 
```


List DR actions available for a specific resource type
--------------------------------------------------

GET /v1/{project_id}/actions/{resource_type_id}

Parameters:
* resource_type_id The unique identifier of the resource type to show actions for 

Result:

```
HTTP/1.1 200 OK

[{Action 1},{Action 2}] 
```


List default DR action of a specific resource type
--------------------------------------------------

GET /v1/{project_id}/get_default_action_for_resource_type/{resource_type_id}

Parameters:
* resource_type_id The unique identifier of the resource type to show action for 

Result:

```
HTTP/1.1 200 OK

[{Action}]
[{"resource_type_id": 1, "class_name": "dragon.workload_policy.actions.plugins.instance_snapshot_action.InstanceSnapshotAction", "created_at": "2015-02-17T18:50:09.653012", "updated_at": "2015-02-17T18:50:09.653019", "id": 2, "name": "Image Snapshot"}] 
```


Mark a resource for DR
-----------------------

```
POST /v1/{tenant_id}/resources

{
    "resource_id": "{resource_id}",
    "resource_name":"{resource_name}",
    "resource_type":"{resource_type}"
}
```

Parameters:
* resource_id The unique identifier of the existing resource to enable dr for 
* resource_name The name of the resource to enable dr for
* resource_type The type of the resource to enable dr for (Instance/Volume/...)

                              
Result:

```
```
                             
List resources marked for DR
----------------------------

GET /v1/{project_id}/resources

Result:

```
HTTP/1.1 200 OK

[{Resource 1},{Resource 2}] 
```

Get resource data
------------------

GET /v1/{project_id}/resources/{resource_id}

Parameters:
* resource_id The unique identifier of the existing resource to enable dr for

Result:

```
HTTP/1.1 200 OK

{Resource} 
```


Create workload policy
------------------------

POST /v1/{project_id}/workload_policies

{
    "tenant_id": "{tenant_id}",
    "name":"{name}",
}
```

Parameters:
* tenant_id The unique identifier of the workload policy's tenant 
* name The name of the workload policy

                              
Result:

```
HTTP/1.1 200 OK
{new workload_policy object}
```

List workload policies
----------------------------

GET /v1/{project_id}/workload_policies

Result:

```
HTTP/1.1 200 OK

[{workload policy 1},{workload policy 2}] 
```

Get wokrload policy data
--------------------------

GET /v1/{project_id}/workload_policies/{workload_policy_id}

Parameters:
* workload_policy_id The unique identifier of the existing workload_policy

Result:

```
HTTP/1.1 200 OK

{workload_policy} 
```


Delete workload policy
-----------------------

```
DELETE /v1/{tenant_id}/workload_policies/{workload_policy_id}
```

Parameters:

* `workload_policy_id` The unique identifier of the workload policy


Result:

```
HTTP/1.1 204 No Content
```

Assign an action to a resource in a workload policy
-------------------------------------------------

POST /v1/{project_id}/resource_action/{resource_id}

{
    "action_id": "{action_id}",
    "workload_policy_id":"{workload_policy_id}",
}
```

Parameters:
* resource_id The unique identifier of the resource
* action_id The unique identifier of the action to perform on the resource 
* workload_policy_id The id of the workload policy the resource belogns to 

                              
Result:

```
HTTP/1.1 200 OK
```

Get wokrload policy's resources
--------------------------
GET /v1/{project_id}/workload_policies/{workload_policy_id}/resource_actions

Parameters:
* workload_policy_id The unique identifier of the workload_policy

Result:

```
HTTP/1.1 200 OK

[{Resource-action}{Resource-action}] 
```

Remove a resource from a workload policy 
-----------------------------------------

DELETE /v1/{project_id}/resource_action/{tuple_id}

{
	"tuple_id":"{tuple_id}",
}
```

Parameters:
* tuple_id The unique identifier of the resource-action

                              
Result:

```
HTTP/1.1 200 OK
```


List workload policy's executions
----------------------------------

GET /v1/{project_id}/workload_policies/{workload_policy_id}/executions

Parameters:
* workload_policy_id The unique identifier of the workload_policy

Result:

```
HTTP/1.1 200 OK

[{workload policy execution}{workload policy execution}] 
```

Get workload policy's execution data
----------------------------------

GET /v1/{project_id}/policy_executions/{policy_execution_id}

Parameters:
* policy_execution_id The unique identifier of the workload_policy's execution

Result:

```
HTTP/1.1 200 OK

[{workload policy execution}] 
```


List workload policy's execution detailed actions status
--------------------------------------------------------
GET /v1/{project_id}/policy_executions/{policy_execution_id}/actions

Parameters:
* policy_execution_id The unique identifier of the workload_policy's execution

Result:

```
HTTP/1.1 200 OK

[{workload policy execution action 1}{workload policy execution action 2}] 
```

Protect a workload policy 
-----------------------------------------

POST /v1/{project_id}/protect/{workload_policy_id}

{
	"consistent":"{consistent}",
}
```

Parameters:
* workload_policy_id The unique identifier of the workload policy to protect
* consistent gurantee a consistenct protect action through all resources in the workload policy True/False
                              
Result:

```
HTTP/1.1 200 OK
```


List all available workload policy executions' container names
--------------------------------------------------------

GET /v1/{project_id}/recovery/policies

Result:

```
HTTP/1.1 200 OK

[{container name 1}{container name 2}] 
```

List workload policy executions' container names for a given workload policy name
--------------------------------------------------------

GET /v1/{project_id}/recovery/policies/{policy_name}/executions

Parameters:
* policy_name workload policy name

Result:

```
HTTP/1.1 200 OK

[{container name 1}{container name 2}] 
```

Recover from a container 
-----------------------------------------

POST /v1/{project_id}/recover

{
	"container_name":"{container_name}",
}
```

Parameters:
* container_name The container name to recover from
                              
Result:

```
HTTP/1.1 200 OK
```
