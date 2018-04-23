import pytest
from _pytest.mark import MarkInfo
from qmcauto import lib
from qmcauto.models.driver import *
from qmcauto.util.network import ping
from qmcauto.util.perfecto import get_allocated_perfecto_devices
from qmcauto.definitions import CONFIG_INI

DEVICES = {} # Is populated by the fixture get_all_devices()
DEVICELIST = []
MARKS = []
IS_PARALLEL = False # Is set to True inside pytest_configure() method
HUB = 0
SETUP_MODE = False
TEST_SET = 0
LOCATION = 'local'  # Location can be 'local' or 'perfecto'

sys.stdout = sys.stderr

logger = logging.getLogger('qmcauto')

def readAllDevices(filters=None):
    """
    :param filters: A list of filters (marks) for devices based on platforms.
    :return: A filtered list of Device objects.
    """
    global DEVICES, MARKS
    logger.debug("Before filterng: {}".format(DEVICES))
    _devices = []
    if filters is None:
        for key in DEVICES:
            _devices.append(DEVICES[key])
    else:

        for tag in ['web', 'android', 'ios','mac']:
            if tag in filters and tag in MARKS:
                for key in DEVICES:
                    if DEVICES[key].getPlatform().lower() == tag.lower() and DEVICES[key].getLocation().lower() == Location.LOCAL.lower():
                        _devices.append(DEVICES[key])

        if 'perfecto' in filters and 'perfecto' in MARKS:
            for key in DEVICES:
                if DEVICES[key].getLocation().lower() == Location.PERFECTO.lower():
                    _devices.append(DEVICES[key])
    logger.debug("Devices: {}".format(_devices))
    return _devices


def pytest_addoption(parser):
    """
    This hook is called to add custom command line arguments.
    :param parser: A instance of the Parser object from pytest package.
                   More: https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.config.Parser
    :return:
    """
    parser.addoption("--hub", action="store", default=0,
        help="Hub id for the tests.")
    parser.addoption("--testset", action="store", default=0,
                     help="Test set id for the test run.")
    parser.addoption("--setup-env", action="store", default=False,
                     help="Setup mode, default is false.")
    parser.addoption("--location", action="store", default='local',
                     help="Location of the test , either local or perfecto.")

def pytest_itemcollected(item):
    pass

def pytest_collection_modifyitems(session, config, items):
    """
    This hook is called after all the test items has been collected.
    :param config:  A Config object from the pytest package.
                    More: https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.config.Config
    :param items:   A list of Node (scripts) objects from pytest package.
                    More: https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.main.Node
    :return:
    """
    if hasattr(config, "slaveinput"):
        for item in items:
            if not item.get_marker(config.slaveinput['platform']):
                item.add_marker(pytest.mark.skip)
    logger.info("Total items collected: {}".format(str(len(items))))


def pytest_generate_tests(metafunc):
    """
    Called each time a test has been collected.
    :param metafunc: A instance of Metafunc object in pytest package.
                     More: https://docs.pytest.org/en/latest/parametrize.html#the-metafunc-object
    :return:
    """
    global IS_PARALLEL
    if 'driver' in metafunc.fixturenames:
        if not IS_PARALLEL:
            marks = [name for name, ob in vars(metafunc.function).items() if isinstance(ob, MarkInfo)]
            _devices = readAllDevices(marks)
            metafunc.parametrize('driver', _devices, indirect=True)

    logger.debug("Parallel Run: {}".format(IS_PARALLEL))


def pytest_configure(config):
    """
    :param config:  A Config object from the pytest package.
                    More: https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.config.Config
    :return:
    """
    global MARKS, HUB, SETUP_MODE, TEST_SET , LOCATION, DEVICELIST
    MARKS = config.getoption("-m").split(",")
    logger.info("Marks: {}".format(MARKS))

    HUB = config.getoption("hub")
    logger.info("Running on HUB {}".format(HUB))

    TEST_SET = config.getoption("testset")
    logger.info("Test set no {}".format(TEST_SET))

    SETUP_MODE = config.getoption("setup_env")
    logger.debug("Setup mode on? {}".format(str(SETUP_MODE)))

    LOCATION = config.getoption("location")
    logger.debug("Location is {}".format(str(LOCATION)))

    get_all_devices()
    if not hasattr(config, "slaveinput"):
        config.devicelist = readAllDevices(MARKS)
        DEVICELIST = config.devicelist
    else:
        global IS_PARALLEL
        IS_PARALLEL = True

def pytest_xdist_setupnodes(config, specs):
    pass

def pytest_xdist_newgateway(gateway):
    global DEVICELIST
    logger.debug("Creating node with id: {}".format(DEVICELIST[-1].getName()))
    gateway.id = DEVICELIST[-1].getName()

def pytest_configure_node(node):
    """
    This hook is called each time a node is started. This hook is from pytest-xdist package.
    Node here refers to a subprocess or slave.
    :param node: A instance of SlaveController object in pytest-xdist package
                 More: https://github.com/pytest-dev/pytest-xdist/blob/master/xdist/slavemanage.py
    :return:
    """
    device = node.config.devicelist.pop()
    logger.info("Starting node with name {}".format(device.getName()))
    node.slaveinput["device"] = device.getName().lower()
    node.slaveinput["platform"] = device.getPlatform().lower()

def pytest_xdist_node_collection_finished(node, ids):
    pass

def pytest_runtest_setup(item):
    pass

@pytest.fixture(autouse=True, scope="session")
def get_all_devices():
    """
    pytest calls it in the beginning to fetch the list of available devices.
    Stores the available devices in the global *DEVICES* dict with device name as key.
    :return: A dict of structure (key, value) = (deviceName: DeviceObject)
    """

    logger.debug("****MARKS****")
    logger.debug(MARKS)

    global DEVICES, HUB, LOCATION
    if "perfecto" in LOCATION.lower():
        perfecto_devices = get_allocated_perfecto_devices()
        for device in perfecto_devices:
            device_name = device['model']+'_'+device['deviceId']
            DEVICES[device_name.lower()] = Device.get(Device.name == device_name)
    else:
        for i in Node.select():
            if int(i.hub.id) == int(HUB):
                if ping(i.ip, i.port):
                    DEVICES[i.device_name.lower()] = Device.get(Device.name == i.device_name)
                    logger.info("Node found at {}:{} for device {}".format(i.ip, i.port, i.device_name))
                else:
                    i.delete_instance()
                    logger.info("Node inactive at {}:{} for device {}, removed.".format(i.ip, i.port, i.device_name))
    return DEVICES


def getAppropriateDriver(_device):
    """
    Instantiates the correct driver for the given device by type checking.
    :param _device: A Device object.
    :return: A Driver object.
    """
    global SETUP_MODE
    if _device.getLocation().lower() == Location.LOCAL.lower():
        if _device.getType().lower() == "smartphone":
            if _device.getPlatform().lower() == Platform.IOS.lower() or _device.getPlatform().lower() == Platform.MAC.lower():
                return IOSDriver(_device, SETUP_MODE, HUB)
            else:
                return AndroidDriver(_device, SETUP_MODE, HUB)
        else:
            return WebDriver(_device, SETUP_MODE, HUB)
    else:
        return PerfectoDriver(_device, SETUP_MODE, HUB)


@pytest.fixture()
def driver(request):
    """
    Returns the appropriate driver based on request.
    :param request: A FixtureRequest object.
                    More: https://docs.pytest.org/en/latest/builtin.html#_pytest.fixtures.FixtureRequest
    :return:
    """
    global TEST_SET
    slaveinput = getattr(request.config, "slaveinput", None)

    if slaveinput is None: # Single process
        _driver = getAppropriateDriver(request.param)
        logger.info("Inside single process.....")
    else: # Parallel
        logger.info("Inside parallel process -> {}".format(str(DEVICES[slaveinput['device']].__dict__)))
        _driver = getAppropriateDriver(DEVICES[slaveinput['device']])

    print("Starting {} for test: {} as part of test set {}".format(_driver.__class__.__name__, request.node.name, TEST_SET))
    print("")

    if _driver.getDevice().getLocation() == 'perfecto':
        machine = "Perfecto"
    else:
        machine = _driver.node.ip
    _driver.start()
    testrun = TestRun2.create(testsetid=int(TEST_SET),
                              device=_driver.getDevice().id,
                              sessionid=_driver.sessionId,
                              script=request.function.__name__,
                              status='running',
                              remarks='',
                              machine=machine)
    testrun.save()
    try:
        yield _driver
        _driver.stop()
    except Exception as e:
        print(e)
    print("after test")
    testrun.endtime = datetime.datetime.now()
    testrun.status = _driver.runStatus.lower()
    if _driver.runStatus.lower() == 'passed':
        testrun.remarks = 'passed'
    else:
        testrun.remarks = _driver.remarks.lower()
    testrun.save()


@pytest.fixture()
def settings(driver):
    """
    Creates a Settings object from lib.
    :param driver: A Driver object.
    :return: A Settings object.
    """
    return lib.Settings.Settings.Settings(driver, driver.getDevice())


@pytest.fixture(scope="session")
def config():
    """
    Loads the configuration from the config.ini file into a configparser object.
    :return: A configparser object.
             More: https://docs.python.org/3/library/configparser.html
    """
    conf = configparser.ConfigParser()
    conf.read(CONFIG_INI)
    return conf
