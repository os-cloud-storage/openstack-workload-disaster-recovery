
Dragon client API
---------

     create_resource(resource_id,  resource_name, resource_type_id)
        - create for a given  triple : resource_id,  resource_name, resource_type_id
        
         :param:  ID of resource
         :param:  Name of resource
         :param:  ID of type of resource
         :rtype: none


     create_resource_action(resource_id,  action_id, workload_policy_id)
        - create for a given  triple: resource_id,  action_id, workload_policy_id
        
         :param:  ID of resource
         :param:  ID of action
         :param:  ID of workload policy
         :rtype: none

     create_workload_policy(policy_name, tenant_id, policy_id)
        - create workload policy
        
         :param:  Name of policy
         :param:  tenant ID
         :rtype:  Policy ID

     delete_resource_action(resource_action_id)
        -  remove a resource from a workload_policy  

          :param: resource_action_id
          :rtype: none

     delete_workload_policy(workload_policy_id)
        - per given workload policy id
        
         :param:  ID of workload policy
         :rtype: none

     get_policy_executions(policy_execution_id )
        -   policy executions of  policy_execution_id
        
         :param:  ID of policy

     get_resource(resource_id )
        - get  resource info for a given resource_id
        
         :param:  ID of resource
         :rtype: resource info: id, type, name

     get_resource_actions( workload_policy_id)
        -  for a given workload_policy_id - get all defined actions
        
         :param:  ID of resource
         :rtype: defined actions information per given workload

     get_workload_policy( workload_policy_id)
        - get policy per given workload policy id
        
         :param:  ID of workload policy
         :rtype:   specified workload policy info

     list_actions( resource_type_id)
        - list_actions for  a given resource type
        
         :param:  ID of resource type
         :rtype:  list of defined actions details  per resource type

     list_policy_executions(workload_policy_id )
        -  for a given workload policy
        
         :param:  ID of workload policy
         :rtype: defined policy workload id information of policy executions

     list_resources( )
        - list all resources
        
         :param: none
         :rtype:  list of resources  (instances, volumes etc.)

     list_workload_policies( )
        - list all workload  policies of current tenant
        
         :param:  none
         :rtype:  All workload policies information

     protect(workload_policy_id, [is_consistent] )
        -  protect a given policy
        
         :param: ID of workload policy
         :param: is consistency required (True/False), will pause relevant VMs
         		 before applying the protect actions on the workload_policy
         :rtype: none

     recover(container_name )
        - recover from a given container
        
         :param: Name of container to recover from
         :rtype: none

	recovery_list_policies()
		- List available workload policy executions' container names

		 :param: None
		 :rtype: container names

	recovery_list_policy_executions(workload_policy_name)
		- List workload policy executions' container names for a given workload policy name

		 :param: workload_policy_name
		 :rtype: container names
