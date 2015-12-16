%global release_name havana
%global release_letter rc
%global milestone 2
%global full_release dragon-%{version}

%global with_doc 0 

Name:		openstack-dragon
Summary:	OpenStack Disaster Recovery  (dragon)
Version:	2015.1.1
Release:	1.3%{?dist}
License:	Apache2
Group:		System Environment/Base
URL:		http://www.openstack.org
Source0:	dragon-%{version}.tar.gz
Provides:	dragon

Source1:	dragon.logrotate
%if 0%{?rhel} && 0%{?rhel} <= 6
Source2:	openstack-dragon-api.init
Source4:	openstack-dragon-engine.init
%else
Source2:	openstack-dragon-api.service
Source4:	openstack-dragon-engine.service
%endif
Source20:   dragon-dist.conf


BuildArch: noarch
BuildRequires: git
BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-argparse
BuildRequires: python-eventlet
BuildRequires: python-greenlet
BuildRequires: python-httplib2
BuildRequires: python-iso8601
BuildRequires: python-kombu
BuildRequires: python-lxml
BuildRequires: python-netaddr
BuildRequires: python-memcached
BuildRequires: python-migrate
BuildRequires: python-qpid
BuildRequires: python-six
BuildRequires: PyYAML
%if 0%{?rhel} && 0%{?rhel} <= 6
%else
%endif
BuildRequires: python-paramiko
# These are required to build due to the requirements check added
BuildRequires: python-paste-deploy
BuildRequires: python-routes
BuildRequires: python-sqlalchemy
BuildRequires: python-webob
BuildRequires: python-pbr
BuildRequires: python-d2to1
%if 0%{?rhel} && 0%{?rhel} <= 6
%else
BuildRequires: systemd-units
%endif
%if 0%{?with_doc}
BuildRequires: python-oslo-config
BuildRequires: python-cinderclient
BuildRequires: python-keystoneclient
BuildRequires: python-novaclient
BuildRequires: python-neutronclient
BuildRequires: python-swiftclient
%endif

Requires: %{name}-common = %{version}-%{release}
Requires: %{name}-engine = %{version}-%{release}
Requires: %{name}-api = %{version}-%{release}

%prep
%setup -q -n %{full_release}


sed -i s/REDHATHEATVERSION/%{version}/ dragon/version.py
sed -i s/REDHATHEATRELEASE/%{release}/ dragon/version.py

# Remove the requirements file so that pbr hooks don't add it
# to distutils requires_dist config
rm -rf {test-,}requirements.txt tools/{pip,test}-requires

echo '
#
# Options to be passed to keystoneclient.auth_token middleware
# NOTE: These options are not defined in dragon but in keystoneclient
#
[keystone_authtoken]

# the name of the admin tenant (string value)
#admin_tenant_name=

# the keystone admin username (string value)
#admin_user=

# the keystone admin password (string value)
#admin_password=

# the keystone host (string value)
#auth_host=

# the keystone port (integer value)
#auth_port=

# protocol to be used for auth requests http/https (string value)
#auth_protocol=

#auth_uri=

# signing_dir is configurable, but the default behavior of the authtoken
# middleware should be sufficient.  It will create a temporary directory
# in the home directory for the user the dragon process is running as.
#signing_dir=/var/lib/dragon/keystone-signing
' >> etc/dragon/dragon.conf.sample

# Programmatically update defaults in sample config
# which is installed at /etc/dragon/dragon.conf
# TODO: Make this more robust
# Note it only edits the first occurance, so assumes a section ordering in sample
# and also doesn't support multi-valued variables.
#while read name eq value; do
#  test "$name" && test "$value" || continue
#  sed -i "0,/^# *$name=/{s!^# *$name=.*!#$name=$value!}" etc/dragon/dragon.conf.sample
#done < %{SOURCE20}

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --root=%{buildroot}
sed -i -e '/^#!/,1 d' %{buildroot}/%{python_sitelib}/dragon/db/sqlalchemy/manage.py
sed -i -e '/^#!/,1 d' %{buildroot}/%{python_sitelib}/dragon/db/sqlalchemy/migrate_repo/manage.py
mkdir -p %{buildroot}/var/log/dragon/
mkdir -p %{buildroot}/var/run/dragon/
install -p -D -m 644 %{SOURCE1} %{buildroot}%{_sysconfdir}/logrotate.d/openstack-dragon

%if 0%{?rhel} && 0%{?rhel} <= 6
# install init scripts
install -p -D -m 755 %{SOURCE2} %{buildroot}%{_initrddir}/openstack-dragon-api
install -p -D -m 755 %{SOURCE4} %{buildroot}%{_initrddir}/openstack-dragon-engine
%else
# install systemd unit files
install -p -D -m 644 %{SOURCE2} %{buildroot}%{_unitdir}/openstack-dragon-api.service
install -p -D -m 644 %{SOURCE4} %{buildroot}%{_unitdir}/openstack-dragon-engine.service
%endif

mkdir -p %{buildroot}/var/lib/dragon/
mkdir -p %{buildroot}/etc/dragon/

%if 0%{?with_doc}
export PYTHONPATH="$( pwd ):$PYTHONPATH"
pushd doc
%if 0%{?rhel} && 0%{?rhel} <= 6
%else
%endif

mkdir -p %{buildroot}%{_mandir}/man1
install -p -D -m 644 build/man/*.1 %{buildroot}%{_mandir}/man1/
popd
%endif

rm -rf %{buildroot}/var/lib/dragon/.dummy
rm -f %{buildroot}/usr/bin/cinder-keystone-setup
rm -rf %{buildroot}/%{python_sitelib}/dragon/tests
rm -f %{buildroot}/usr/bin/dragon-db-setup

install -p -D -m 640 %{_builddir}/%{full_release}/etc/dragon/dragon.conf %{buildroot}/%{_sysconfdir}/dragon/dragon.conf
install -p -D -m 640 %{SOURCE20} %{buildroot}%{_datadir}/dragon/dragon-dist.conf
install -p -D -m 640 %{_builddir}/%{full_release}/etc/dragon/api-paste.ini %{buildroot}/%{_sysconfdir}/dragon/api-paste.ini
install -p -D -m 640 %{_builddir}/%{full_release}/etc/dragon/api-paste.ini %{buildroot}/%{_datadir}/dragon/api-paste-dist.ini
#install -p -D -m 640 etc/dragon/policy.json %{buildroot}/%{_sysconfdir}/dragon


%description
Dragon provides disaster recovery OpenStack.


%package common
Summary: Dragon common
Group: System Environment/Base

Requires: python-argparse
Requires: python-eventlet
Requires: python-greenlet
Requires: python-httplib2
Requires: python-iso8601
Requires: python-kombu
Requires: python-lxml
Requires: python-netaddr
Requires: python-paste-deploy
Requires: python-cinderclient
Requires: python-keystoneclient
Requires: python-memcached
Requires: python-novaclient
Requires: python-oslo-config >= 1:1.2.0
Requires: python-neutronclient
Requires: python-swiftclient
Requires: python-routes
Requires: python-sqlalchemy
Requires: python-migrate
Requires: python-qpid
Requires: python-webob
Requires: python-six
Requires: PyYAML
Requires: m2crypto
Requires: python-anyjson
Requires: python-paramiko
#Requires: python-dragonclient
Requires: python-babel
Requires: MySQL-python
Requires: python-ipaddr

Requires(pre): shadow-utils

%description common
Components common to all OpenStack Dragon services

%files common
%doc LICENSE
%{_bindir}/dragon-manage
%{_bindir}/dragon-keystone-setup
%{python_sitelib}/dragon*
%attr(-, root, dragon) %{_datadir}/dragon/dragon-dist.conf
%attr(-, root, dragon) %{_datadir}/dragon/api-paste-dist.ini
%dir %attr(0755,dragon,root) %{_localstatedir}/log/dragon
%dir %attr(0755,dragon,root) %{_localstatedir}/run/dragon
%dir %attr(0755,dragon,root) %{_sharedstatedir}/dragon
%dir %attr(0755,dragon,root) %{_sysconfdir}/dragon
%config(noreplace) %{_sysconfdir}/logrotate.d/openstack-dragon
%config(noreplace) %attr(-, root, dragon) %{_sysconfdir}/dragon/dragon.conf
%config(noreplace) %attr(-, root, dragon) %{_sysconfdir}/dragon/api-paste.ini
#%config(noreplace) %attr(-, root, dragon) %{_sysconfdir}/dragon/policy.json
#%config(noreplace) %attr(-,root,dragon) %{_sysconfdir}/dragon/environment.d/*
#%config(noreplace) %attr(-,root,dragon) %{_sysconfdir}/dragon/templates/*
%if 0%{?with_doc}
%{_mandir}/man1/dragon-keystone-setup.1.gz
%endif

%pre common
# 187:187 for dragon - rhbz#845078
getent group dragon >/dev/null || groupadd -r --gid 187 dragon
getent passwd dragon  >/dev/null || \
useradd --uid 187 -r -g dragon -d %{_sharedstatedir}/dragon -s /sbin/nologin \
-c "OpenStack Dragon Daemons" dragon
exit 0

%package engine
Summary: The Dragon engine
Group: System Environment/Base

Requires: %{name}-common = %{version}-%{release}

%if 0%{?rhel} && 0%{?rhel} <= 6
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
Requires(postun): initscripts
%else
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%endif

%description engine
OpenStack API for starting disaster recovery on OpenStack

%files engine
%doc README.rst LICENSE
%if 0%{?with_doc}
%doc doc/build/html/man/dragon-engine.html
%endif
%{_bindir}/dragon-engine
%if 0%{?rhel} && 0%{?rhel} <= 6
%{_initrddir}/openstack-dragon-engine
%else
%{_unitdir}/openstack-dragon-engine.service
%endif
%if 0%{?with_doc}
%{_mandir}/man1/dragon-engine.1.gz
%endif

%post engine
%if 0%{?rhel} && 0%{?rhel} <= 6
/sbin/chkconfig --add openstack-dragon-engine
%else
%systemd_post openstack-dragon-engine.service
%endif

%preun engine
%if 0%{?rhel} && 0%{?rhel} <= 6
if [ $1 -eq 0 ]; then
    /sbin/service openstack-dragon-engine stop >/dev/null 2>&1
    /sbin/chkconfig --del openstack-dragon-engine
fi
%else
%systemd_preun openstack-dragon-engine.service
%endif

%postun engine
%if 0%{?rhel} && 0%{?rhel} <= 6
if [ $1 -ge 1 ]; then
    /sbin/service openstack-dragon-engine condrestart >/dev/null 2>&1 || :
fi
%else
%systemd_postun_with_restart openstack-dragon-engine.service
%endif


%package api
Summary: The Dragon API
Group: System Environment/Base

Requires: %{name}-common = %{version}-%{release}

%if 0%{?rhel} && 0%{?rhel} <= 6
Requires(post): chkconfig
Requires(preun): chkconfig
Requires(preun): initscripts
Requires(postun): initscripts
%else
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd
%endif

%description api
OpenStack-native ReST API to the Dragon Engine

%files api
%doc README.rst LICENSE
%if 0%{?with_doc}
%doc doc/build/html/man/dragon-api.html
%endif
%{_bindir}/dragon-api
%if 0%{?rhel} && 0%{?rhel} <= 6
%{_initrddir}/openstack-dragon-api
%else
%{_unitdir}/openstack-dragon-api.service
%endif
%if 0%{?with_doc}
%{_mandir}/man1/dragon-api.1.gz
%endif

%post api
%if 0%{?rhel} && 0%{?rhel} <= 6
/sbin/chkconfig --add openstack-dragon-api
%else
%systemd_post openstack-dragon-api.service
%endif

%preun api
%if 0%{?rhel} && 0%{?rhel} <= 6
if [ $1 -eq 0 ]; then
    /sbin/service openstack-dragon-api stop >/dev/null 2>&1
    /sbin/chkconfig --del openstack-dragon-api
fi
%else
%systemd_preun openstack-dragon-api.service
%endif

%postun api
%if 0%{?rhel} && 0%{?rhel} <= 6
if [ $1 -ge 1 ]; then
    /sbin/service openstack-dragon-api condrestart >/dev/null 2>&1 || :
fi
%else
%systemd_postun_with_restart openstack-dragon-api.service
%endif


