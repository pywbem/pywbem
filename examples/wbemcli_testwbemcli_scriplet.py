"""
    Pywbem wbemcli scriptlet that tests wbemcli shortcut methods.  The
    goal of this scriptlet is to test the parameters for all of the
    shortcut methods in wbemcli to assure that the names are correct and
    that they execute.  This does not guarantee that the results are always
    correct.

    This scriptlet requires a running server.

    It also depends heavily on the existence of the PyWBEM special
    classes and instances in the server.

    This scriptlet executes an assert to test results but does NOT use
    the python unittest library.

    NOTE: TODO does not test the create/delete functions for instances,
           classes or QualifierDeclarations.
"""
from wbemcli import CONN, gc, ecn, ei, iei, oei, piwp, ein, ieip, oeip, pip, \
    a, iai, oai, an, iaip, oaip, iri, ori, rn, irip, orip, ec, gq, eq

# test objects
# live class against the server. may not always return same number of elements
TEST_CLASS1 = 'CIM_ManagedElement'
# class that returns a defined set of elements
TEST_CLASS2 = 'PyWBEM_Person'
TEST_CLASS2_PROPERTIES = ['Name', 'CreationClassName']

# pywbem test classes. Can be used to test associations because association
# definitions are specific.
PYWBEM_PERSON_CLASS = "PyWBEM_Person"
PYWBEM_PERSON_PROPERTIES = ['InstanceId', 'CreationClassName']
PYWBEM_PERSONCOLLECTION = "PyWBEM_PersonCollection"
PYWBEM_MEMBEROFPERSONCOLLECTION = "PyWBEM_MemberOfPersonCollection"
PYWBEM_SOURCE_ROLE = "member"
PYWBEM_TARGET_ROLE = "collection"
PERSON_COUNT = 3


def test_enum_insts(cn, ns=None, lo=None, iq=None, ico=None, pl=None, fl=None,
                    fq=None, ot=None, coe=None, moc=1, mop=10, exp_count=None):
    """
    Function to execute all 3 types of enumerate instances and compare
    results. Executes EnumerateInstances, Open/Pull instances with path and
    IterEnumerateInstances and compares to see if the same number of instances
    received.
    """
    insts_ei = ei(cn, ns=ns, lo=lo, iq=iq, ico=ico, pl=pl)
    assert len(insts_ei) > 0
    if exp_count:
        assert exp_count == len(insts_ei)

    if pl is not None:
        # test for existence of first property
        for prop in pl:
            # test that all properties in list are returned
            pls = [inst[prop] for inst in insts_ei]
            assert len(pls)
        for inst in insts_ei:
            assert len(inst.properties) == len(pl)

    insts_iei = [inst for inst in iei(cn, ns=ns, lo=lo, iq=iq, ico=ico,
                                      pl=pl, fl=fl, fq=fq, ot=ot, coe=coe,
                                      moc=moc)]
    assert len(insts_ei) == len(insts_iei)
    result = oei(cn, ns=ns, lo=lo, iq=iq, ico=ico, pl=pl, fl=fl, fq=fq,
                 ot=ot, coe=coe, moc=moc)
    insts_pei = result.instances
    while not result.eos:
        result = piwp(result.context, moc=mop)
        insts_pei.extend(result.instances)
    assert len(insts_ei) == len(insts_pei)


def test_enum_instpaths(cn, ns=None, fl=None, fq=None, ot=None, coe=None,
                        moc=1, mop=10, exp_count=None):
    """
    Function to execute all 3 types of enumerate instances and compare
    results.
    """
    insts_ei = ein(cn, ns=ns)
    assert len(insts_ei) > 0
    if exp_count:
        exp_count = len(insts_ei)

    insts_iei = [inst for inst in ieip(cn, ns=ns, fl=fl, fq=fq, ot=ot,
                                       coe=coe, moc=moc)]
    assert len(insts_ei) == len(insts_iei)
    result = oeip(cn, ns=ns, fl=fl, fq=fq, ot=ot, coe=coe, moc=moc)
    insts_pei = result.paths
    while not result.eos:
        result = pip(result.context, moc=mop)
        insts_pei.extend(result.paths)
    assert len(insts_ei) == len(insts_pei)


def test_instassocs(cn, ac=None, rc=None, r=None, rr=None, iq=None, ico=None,
                    pl=None, fl=None, fq=None, ot=None, coe=None, moc=None,
                    mop=10, exp_count=None):  # pylint: disable=invalid-name
    """
    Function to execute all 3 types of enumerate instance paths and compare
    results.
    """
    # first get an instance to work with
    paths_ei = ein(cn)
    assert len(paths_ei) > 0
    tst_path = paths_ei[0]

    insts_a = a(tst_path, ac=ac, rc=rc, r=r, rr=rr, iq=iq, ico=ico,
                pl=pl)
    if not moc:
        moc = 1
    insts_iai = [inst for inst in iai(tst_path, ac=ac, rc=rc, r=r, rr=rr,
                                      iq=iq, ico=ico, pl=pl, fl=fl, fq=fq,
                                      ot=ot, coe=coe, moc=moc)]
    if exp_count:
        assert exp_count == len(insts_a)

    assert len(insts_a) == len(insts_iai)
    # get with pull operations
    result = oai(tst_path, ac=ac, rc=rc, r=r, rr=rr, iq=iq, ico=ico, pl=pl,
                 fl=fl, fq=fq, ot=ot, coe=coe, moc=moc)
    insts_pai = result.instances
    while not result.eos:
        result = piwp(result.context, moc=mop)
        insts_pai.extend(result.instances)
    assert len(insts_a) == len(insts_pai)


def test_instassocpaths(cn, ac=None, rc=None, r=None, rr=None,
                        fl=None, fq=None, ot=None, coe=None, moc=None, mop=10,
                        exp_count=None):  # pylint: disable=invalid-name
    """
    Function to execute all 3 types of enumerate instance paths  requests
    and compare results.
    """
    # first get an instance to work with
    paths_ei = ein(cn)
    assert len(paths_ei) > 0
    tst_path = paths_ei[0]

    paths_an = an(tst_path, ac=ac, rc=rc, r=r, rr=rr)
    if not moc:
        moc = 1
    paths_iai = [path for path in iaip(tst_path, ac=ac, rc=rc, r=r, rr=rr,
                                       fl=fl, fq=fq, ot=ot, coe=coe, moc=moc)]
    if exp_count:
        assert exp_count == len(paths_an)

    assert len(paths_an) == len(paths_iai)
    # get with pull operations
    result = oaip(tst_path, ac=ac, rc=rc, r=r, rr=rr, fl=fl,
                  fq=fq, ot=ot, coe=coe, moc=moc)
    paths_pai = result.paths
    while not result.eos:
        result = pip(result.context, moc=mop)
        paths_pai.extend(result.paths)
    assert len(paths_an) == len(paths_pai)


def test_instrefs(cn, rc=None, r=None, iq=None, ico=None,
                  pl=None, fl=None, fq=None, ot=None, coe=None, moc=None,
                  mop=10, exp_count=None):
    """
    Function to execute all 3 types of enumerate instance paths and compare
    results. This test function takes a class as input and get the first
    instance of that class for the reference call.
    """
    # first get an instance to work with
    paths_ei = ein(cn)
    assert len(paths_ei) > 0
    tst_path = paths_ei[0]

    # TODO using r here causes failure with non-callable object
    insts_r = CONN.References(tst_path, ResultClass=rc, Role=r,
                              IncludeQualifiers=iq, IncludeClassOrigin=ico,
                              PropertyList=pl)
    if not moc:
        moc = 1
    insts_iri = [inst for inst in iri(tst_path, rc=rc, r=r,
                                      iq=iq, ico=ico, pl=pl, fl=fl, fq=fq,
                                      ot=ot, coe=coe, moc=moc)]
    if exp_count:
        assert exp_count == len(insts_r)
    assert len(insts_r) == len(insts_iri)
    # get with pull operations
    result = ori(tst_path, rc=rc, r=r, iq=iq, ico=ico, pl=pl,
                 fl=fl, fq=fq, ot=ot, coe=coe, moc=moc)
    insts_pri = result.instances
    while not result.eos:
        result = piwp(result.context, moc=mop)
        insts_pri.extend(result.instances)
    assert len(insts_r) == len(insts_pri)


def test_instrefpaths(cn, rc=None, r=None,
                      fl=None, fq=None, ot=None, coe=None, moc=None, mop=10,
                      exp_count=None):  # pylint: disable=invalid-name
    """
    Function to execute all 3 types of enumerate instance paths and compare
    results.
    """
    # first get an instance to work with
    paths_ei = ein(cn)
    assert len(paths_ei) > 0
    tst_path = paths_ei[0]

    paths_rn = rn(tst_path, rc=rc, r=r)
    if not moc:
        moc = 1
    paths_irip = [path for path in irip(tst_path, rc=rc, r=r,
                                        fl=fl, fq=fq, ot=ot, coe=coe, moc=moc)]
    if exp_count:
        assert exp_count == len(paths_rn)

    assert len(paths_irip) == len(paths_irip)
    # get with pull operations
    result = orip(tst_path, rc=rc, r=r, fl=fl,
                  fq=fq, ot=ot, coe=coe, moc=moc)
    paths_pai = result.paths
    while not result.eos:
        result = pip(result.context, moc=mop)
        paths_pai.extend(result.paths)
    assert len(paths_rn) == len(paths_pai)


# test getclass
cl = gc(PYWBEM_PERSON_CLASS)  # pylint: disable=invalid-name
assert cl.classname == PYWBEM_PERSON_CLASS

# test enumerate classnames
clns = ecn()  # pylint: disable=invalid-name
assert 'CIM_ManagedElement' in clns

# test enumerate classes
cls = ec()  # pylint: disable=invalid-name
assert cls

# test get QualifierDeclarations
qd = gq('Abstract')  # pylint: disable=invalid-name
assert qd

# test enumerate qualifierdeclarations
qds = eq()  # pylint: disable=invalid-name
assert qds

# Tests executed against the common function to test enumerate instances
# This tests EnumerateInstances, Open/PullEnumerateInstances, and
# IterEnumerateInstances
test_enum_insts(TEST_CLASS2)
test_enum_insts(TEST_CLASS2, pl=TEST_CLASS2_PROPERTIES)
# this one returns error LocalOnly not supported???
# test_enum_insts(TEST_CLASS2, pl=TEST_CLASS2_PROPERTIES, lo=True)
test_enum_insts(TEST_CLASS2, pl=[TEST_CLASS2_PROPERTIES[0]])
test_enum_insts(TEST_CLASS2, iq=True)
test_enum_insts(TEST_CLASS2, iq=False)
test_enum_insts(TEST_CLASS2, ico=True)
test_enum_insts(TEST_CLASS2, ico=False)
# TODO not testing fq, fl, coe, ot, ns

# Test that the following returns the correct count
test_enum_insts(PYWBEM_PERSON_CLASS, exp_count=PERSON_COUNT)

# Test enumerate paths functions
# TODO not testing ns
test_enum_instpaths(TEST_CLASS2)

# Test association functions
# TODO not testing fq, fl, ot coe
test_instassocs(PYWBEM_PERSON_CLASS)
test_instassocs(PYWBEM_PERSON_CLASS, ot=30)
test_instassocs(PYWBEM_PERSON_CLASS, exp_count=1)
test_instassocs(PYWBEM_PERSON_CLASS, exp_count=1,
                ac=PYWBEM_MEMBEROFPERSONCOLLECTION,
                rc=PYWBEM_PERSONCOLLECTION,
                r=PYWBEM_SOURCE_ROLE,
                rr=PYWBEM_TARGET_ROLE)

test_instassocpaths(PYWBEM_PERSON_CLASS)
test_instassocpaths(PYWBEM_PERSON_CLASS, exp_count=1)
test_instassocpaths(PYWBEM_PERSON_CLASS, exp_count=1,
                    ac=PYWBEM_MEMBEROFPERSONCOLLECTION,
                    rc=PYWBEM_PERSONCOLLECTION,
                    r=PYWBEM_SOURCE_ROLE,
                    rr=PYWBEM_TARGET_ROLE)

# Test reference functions
test_instrefs(PYWBEM_PERSON_CLASS)
test_instrefs(PYWBEM_PERSON_CLASS, exp_count=1)
test_instrefs(PYWBEM_PERSON_CLASS, exp_count=1,
              rc=PYWBEM_MEMBEROFPERSONCOLLECTION,
              r=PYWBEM_SOURCE_ROLE)

test_instrefpaths(PYWBEM_PERSON_CLASS)
test_instrefpaths(PYWBEM_PERSON_CLASS, exp_count=1)
test_instrefpaths(PYWBEM_PERSON_CLASS, exp_count=1,
                  rc=PYWBEM_MEMBEROFPERSONCOLLECTION,
                  r=PYWBEM_SOURCE_ROLE)

print('Test successful. Quitting')
quit()
