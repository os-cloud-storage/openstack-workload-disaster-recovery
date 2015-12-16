Prerequisites:
Services installed: swift, openstack core services (nova, cinder, ..), heat
Openstack release: Kilo 
Openstack installed and all services are up and running (including cinder-backup service and Swift)
You will need the mysql username and password for creating the dr database scheme stage
You will need the rabbit service password and port to configure dragon.conf 
An available port for dr api service to listen to (default is 8007)
 
* Install DRBD

* Install Dragon
(note: this guide can be found under tools/config)
rpm -i openstack-dragon-common-2015.1.1-1.3.el7.noarch.rpm
rpm -i python-dragonclient-2015.1.1-2.el7.noarch.rpm
rpm -i openstack-dragon-engine-2015.1.1-1.3.el7.noarch.rpm
rpm -i openstack-dragon-api-2015.1.1-1.3.el7.noarch.rpm

Authenticate to keystone as admin (by: source /root/openrc) and do:
export SERVICE_HOST=$your_host_ip
*Run: /usr/bin/dragon-keystone-setup
Verify with keystone command line: keystone service-list that dragon service is registered with keystone 

Configure /etc/dragon/dragon.conf: 
bind_host in [dragon_api] section,
auth_host, auth_uri, admin_password and admin_tenant_name in [keystone_authtoken] section 
remote swift parameters (backup_swift_url, backup_swift_key) in [default] section
set db parameters (db_connection)  
set rpc_backend according to the openstack installation setup (amqp/qpid), as well as other rpc relevant parameter (rabbit_host, rabbit_port, rabbit_use_ssl, rabbit_userid, rabbit_password) in [oslo.messaging] section
 
Make sure the following python lib exists, if not, install them:
easy_install PasteDeploy
easy_install routes

* Create Dragon db with tables, etc as follows:

 mysql --user=root --password=$password
>create database dragon CHARACTER SET utf8;
>CREATE USER 'dragon'@'localhost' IDENTIFIED BY 'dragon';
>GRANT ALL PRIVILEGES ON * . * TO 'dragon'@'localhost';
> FLUSH PRIVILEGES;
to delete a user : > DROP user dragon;

Now cerate the Dragon db tables as follows (the OS way):

-cd /usr/lib/python2.7/site-packages/dragon/db/sqlalchemy/migrate_repo

-run : python manage.py version_control   i.e establish db version control here   

    check the base version is 0 by:
    python manage.py db_version    (returned result should be 0)  
    
-now from migrate_repo directory run: python manage.py upgrade
	This will generate 7 tables and also initialize the 2 tables : 'resource_types' and 'actions' with default values 
	
	the following  should  be printed on console: 
	 0 -> 1...
	 done


	if you need to downgrade DB version (go back  to old version) run : 
	
	   python manage.py downgrade 0      i.e downgrade to version control 0

Flame:
    Dragon uses Cloudwatt's Flame for template generation.
    Download flame.py and managers.py from https://github.com/cloudwatt/flame/blob/master/flameclient/
    Include the files in dragon.template package
    Apply patches to those files if applicable (we provide patches for cinderv2 use and Openstack version upgrade in dragon/contrib)

Start the dragon services:  
service openstack-dragon-engine start
service openstack-dragon-api start
check that /var/log/dragon/api.log and   /var/log/dragon/engine.log has no ERROR or Traceback

Test Dragon install successfully: 
	  dragon list-actions 1 
      dragon list-actions 2


* Install Dashboard
Extract file dragon-dashboard-2014.3.1.tar.gz 
copy all dirs content from dragon-2014.3.1/contrib/horizon/openstack_dashboard/ one by one to the corresponding  
   /usr/share/openstack-dashboard/openstack_dashboard/   directories (api, enabled and dashboards/project)


 restart the httpd service : service httpd restart

 check that no errors appear at : /var/log/httpd/openstack-dashboard-access.log or /var/log/httpd/openstack-dashboard-error.log

* Update Cinder

Make sure cinder-backup service section was configured:
     Configure cinder.conf section "Options defined in cinder.backup.drivers.swift", see example in tools/config/sample_conf_files/cinder.conf.sample
	 Parameters: cinder.backup.drivers.swift, backup_swift_key, ...

Extract file dragon-cinder-2015.1.1.tar.gz
Copy cinder/volume/drivers/drbdmanagedrv.py to cinder directory volume drivers location (.../pythonX/../cinder/volume/drivers)

Create drbd volume_type in cinder:
cinder type-create drbddriver-1

Update cinder.conf with drbd driver:
default_volume_type = drbddriver-1
enabled_backends = drbddriver-1 (for list add it with a comma in the end, i.e. enabled_backends = lvm,drbddriver-1)
 
[drbddriver-1]
iscsi_helper = tgtadm
volume_group = drbdpool
volume_driver = cinder.volume.drivers.drbdmanagedrv.DrbdManageDriver
volume_backend_name = drbddriver-1

run the following command to assign extra-spec to drbddriver-1:
cinder type-key drbddriver-1 set volume_backend_name=drbdmanage

Allow the user to access the drbdmanage service. Add the following section to the file /etc/dbus-1/system.d/org.drbd.drbdmanaged.conf:
<policy user="cinder">
      <allow own="org.drbd.drbdmanaged"/>
      <allow send_interface="org.drbd.drbdmanaged"/>
      <allow send_destination="org.drbd.drbdmanaged"/>
</policy>

Restart Cinder's services:
service openstack-cinder-backup restart
service openstack-cinder-api restart
service openstack-cinder-volume restart
verify by : cinder service-list   that the cinder services are up and running 

Run system test to test end to end (including Swift) 
 
Problem solving:
*1. In case of error when running dragon-keystone-setup where SERVICE_TENANT is empty and therefore keystone user-create fails, 
type keystone tenant-list and change the dragon-keystone-setup line SERVICE_TENANT=$(get_data 2 service 1 keystone tenant-list) in keystone_setup method 
according to the name field (i.e. services in the below sample)
 
+----------------------------------+---------------+---------+
|                id                |      name     | enabled |
+----------------------------------+---------------+---------+
| 98920d5154e148209542c1a0cd79bc72 | DeutscheWelle |   True  |
| 1670f0e56fb6421cb83d81b60b149c04 |     admin     |   True  |
| 82f5ac818d42400a8d3194269a9785b4 |      demo     |   True  |
| d1d65b6feab741a6a2905e6197cb15ee |    services   |   True  |
+----------------------------------+---------------+---------+