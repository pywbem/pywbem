%global py3_build_dir %{_builddir}/%{name}-%{version}-%{release}-python3

Name:           pywbem
Version:        %{getenv:PYWBEM_VERSION}
Release:        1%{?dist}
Summary:        Python2 WBEM Client and Provider Interface
Group:          Development/Libraries
License:        LGPLv2
URL:            https://github.com/pywbem/pywbem
Source0:        https://github.com/pywbem/pywbem/archive/%{version}.tar.gz
BuildRequires:  python2-pip
BuildRequires:  python2-pyyaml python2-ply python2-rpm-macros
BuildRequires:  python3-pip python3-PyYAML python3-ply python3-rpm-macros
BuildRequires:  python3-pbr python2-pbr
BuildArch:      noarch

%global _description\
A Python library for making CIM (Common Information Model) operations over HTTP\
using the WBEM CIM-XML protocol. It is based on the idea that a good WBEM\
client should be easy to use and not necessarily require a large amount of\
programming knowledge. It is suitable for a large range of tasks from simply\
poking around to writing web and GUI applications.\
\
WBEM, or Web Based Enterprise Management is a manageability protocol, like\
SNMP, standardized by the Distributed Management Task Force (DMTF) available\
at http://www.dmtf.org/standards/wbem.\
\
It also provides a Python provider interface, and is the fastest and\
easiest way to write providers on the planet.

%description %_description

%package -n python2-pywbem
Summary: %summary
Requires:       m2crypto python2-pyyaml python2-six python2-ply
%{?python_provide:%python_provide python2-pywbem}
# Remove before F30
Provides: pywbem%{?_isa} = %{version}-%{release}
Obsoletes: pywbem < %{version}-%{release}

%description -n python2-pywbem %_description

%package -n python3-pywbem
Group:          Development/Libraries
Summary:        Python3 WBEM Client and Provider Interface
BuildArch:      noarch
Requires:       python3-PyYAML python3-six python3-ply

%description -n python3-pywbem
A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards DSP0200
and DSP0201. The CIM/WBEM infrastructure is used for a wide variety of systems
management tasks supported by systems running WBEM servers. See WBEM Standards
for more information about WBEM.

%prep
%setup -q -n %{name}-%{version}
echo pwd=$(pwd)
echo py3_build_dir=%{py3_build_dir}
echo __python2=%{__python2}
echo __python3=%{__python3}

%build
cp -a . %{py3_build_dir}
PBR_VERSION="%{version}" CFLAGS="%{optflags}" %{__python2} setup.py build
pushd %{py3_build_dir}
PBR_VERSION="%{version}" CFLAGS="%{optflags}" %{__python3} setup.py build
popd

%install
rm -rf %{buildroot}
env PYTHONPATH=%{buildroot}/%{python2_sitelib} \
    PBR_VERSION="%{version}" \
    %{__python2} setup.py install -O1 --skip-build --root %{buildroot}
rm -rf %{buildroot}/usr/bin/
install -m644 LICENSE.txt \
    %{buildroot}/%{python2_sitelib}/pywbem/LICENSE.txt
pushd %{py3_build_dir}
env PYTHONPATH=%{buildroot}/%{python3_sitelib} \
    PBR_VERSION="%{version}" \
    %{__python3} setup.py install -O1 --skip-build --root %{buildroot}
install -m644 LICENSE.txt \
    %{buildroot}/%{python3_sitelib}/pywbem/LICENSE.txt
rm -rf %{buildroot}/usr/bin/*.bat
popd

%files -n python2-pywbem
%{python2_sitelib}/*.egg-info
%{python2_sitelib}/pywbem/
%{python2_sitelib}/pywbem_mock/

%files -n python3-pywbem
%{python3_sitelib}/*.egg-info
%{python3_sitelib}/pywbem/
%{python3_sitelib}/pywbem_mock/
%{_bindir}/mof_compiler
%{_bindir}/wbemcli
%{_bindir}/wbemcli.py
%doc README.rst

%changelog
# insert your distro change log here
