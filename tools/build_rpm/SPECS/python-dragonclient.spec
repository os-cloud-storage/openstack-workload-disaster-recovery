Name:    python-dragonclient
Version: 2015.1.1
Release: 2%{?dist}
Summary: Python API and CLI for OpenStack Dragon

Group:   Development/Languages
License: Apache2
URL:     http://pypi.python.org/pypi/python-dragonclient
Source0: python-dragonclient-%{version}.tar.gz
#
#

BuildArch: noarch

BuildRequires: python2-devel
BuildRequires: python-setuptools
BuildRequires: python-d2to1
BuildRequires: python-pbr

Requires: python-argparse
Requires: python-httplib2
Requires: python-iso8601
Requires: python-keystoneclient
Requires: python-prettytable
Requires: python-six

%description
This is a client for the OpenStack Dragon API. There's a Python API (the
dragonclient module), and a command-line script (dragon). Each implements 100% of
the OpenStack Dragon API.


%prep
%setup -q


# We provide version like this in order to remove runtime dep on pbr.
sed -i s/REDHATHEATCLIENTVERSION/%{version}/ dragonclient/__init__.py

%build
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --root %{buildroot}
echo "%{version}" > %{buildroot}%{python_sitelib}/dragonclient/versioninfo

# Delete tests
rm -fr %{buildroot}%{python_sitelib}/dragonclient/tests

export PYTHONPATH="$( pwd ):$PYTHONPATH"
#sphinx-1.0-build -b html doc/source html

# Fix hidden-file-or-dir warnings
rm -fr html/.doctrees html/.buildinfo

%files
%doc LICENSE 
#README.rst
%{_bindir}/dragon
%{python_sitelib}/dragonclient
%{python_sitelib}/*.egg-info

