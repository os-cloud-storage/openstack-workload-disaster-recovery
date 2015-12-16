.. dragon documentation master file, created by
   sphinx-quickstart on Mon Oct 27 11:13:21 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

IBM   with OpenStack Disaster Recovery Tech Preview Documentation
==================================

IBM  's Disaster Recovery is a service that enables Disaster Recovery for Openstack workloads.

What is the purpose of the project and vision for it?
=====================================================

* IBM  's Disaster Recovery provides an API and panels in Horizon to specify workload protection policies and triggering them by executing appropriate :term:`OpenStack` API calls to protect running cloud applications.

* Currently cloud applications are protected by storing their resources and metadata in a shared object storage at a third party location. Protected applications can be restored on any OpenStack cloud having access to the shared object storage.

* The software integrates other core components of OpenStack into unified system. IBM  's Disaster Recovery allows to protect and restore most OpenStack resource types (such as instances, volumes, security groups, users, etc).

This documentation offers information on how IBM  's Disaster Recovery works and how to install and use it.

How it Works
------------

* IBM's Disaster Recovery is an admin tool that natively supports multi-tenancy.
* It runs as a service registered in the OpenStack system (through keystone) and it can access the list of resources (instances, volumes, security groups, public keys) of each tenant accessible by the admin user
* An admin user can switch to a specific tenant and create one (or more) workload protection policies. A policy is a collection of resources with associated resource actions. A resource action provides the implementation of the "protect" and "restore" logic for a specific resource type.
* For instance, in the current implementation of dragon, for a resource of type volume (a volume in cinder) the current default action is called "volume snapshot ". The "protect" logic of this action first creates a clone of the volume, then uses cinder-backup to export the clone data to a remote swift, then saves the cinder-backup metadata to swift. Conversely the "restore" logic is able to import the cinder-backup metadata from swift into a cinder instance and then invoke the restoration of the volume from swift.
* The admin user can manually trigger a workload protection policy and check the status of execution of the protect tasks for each resource and associated action. Once a protection policy has been correctly executed, the metadata needed to restore the protected resources is saved to a configurable third party object container (swift)
* The recover scenario requires authenticated access to the object container from a dragon instance typically on a secondary (recovery) site. Using the same tenant for which a protection policy was executed, the admin user is able to retrieve a list of successful protection policy executions and restore a point in time
* Point in time restore reads the metadata of the protected resources from swift, invokes the restore steps for each action associated to a resource, and finally triggers the deployment of the protected workload through heat

Getting Started
===============

.. toctree::
    :maxdepth: 1

    chef_install/chef_install


Developers Documentation
========================
.. toctree::
   :maxdepth: 1

   architecture/index

API Documentation
========================
.. toctree::
   :maxdepth: 1

   api
   dragonclient_api

Operations Documentation
========================
.. toctree::
   :maxdepth: 1

   protect_workload/index
   recover_workload/recover
   periodic_protect


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

