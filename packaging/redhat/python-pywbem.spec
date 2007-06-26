%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           python-pywbem
Version:        0.5
Release:        1%{?dist}
Summary:        Python WBEM Client

Group:          Development/Languages
License:        LGPL
URL:            http://pywbem.sourceforge.net
Source0:        pywbem-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel

Requires: python >= 2.3

%description
PyWBEM is a Python library for making CIM operations over HTTP using the 
WBEM CIM-XML protocol.  WBEM is a manageability protocol, like SNMP,
standardised by the Distributed Management Task Force (DMTF) available
at http://www.dmtf.org/standards/wbem.

%prep
%setup -q -n pywbem-%{version}

%build
CFLAGS="%{optflags}" %{__python} setup.py build

%install
rm -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc README

%{python_sitelib}/pywbem

%changelog
* Tue Jun 26 2007 Tim Potter <tpot@hp.com> - 0.5-1
- Initial packaging
