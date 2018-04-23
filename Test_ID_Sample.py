import logging
import pytest
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
import sys
sys.path.append(dir_path + "/../")
import qmcauto.lib
import qmcauto.objectrepo.ui.MasterDetail
import qmcauto.objectrepo.ui.ContentPage

class TestSample:
    """
       Add appropriate marker in the *pytestmark* list. Choose from the below list -
       Markers: android, ios, web, perfecto, local
       When adding to the list concat the mark with the following prefix "pytest.mark.".
       If you choose to add "android" then put "pytest.mark.android" in the list.

       E.g. pytestmark = [pytest.mark.android, pytest.mark.perfecto]
       """
    pytestmark = [pytest.mark.ios, pytest.mark.android, pytest.mark.web, pytest.mark.perfecto]

    def setup(self):
        """

        :return: Void
        """
        logging.debug("Setting up for test %s", self.__class__.__name__)

    def teardown(self):
        """

        :return: Void
        """
        logging.debug("Tearing down test %s", self.__class__.__name__)

    def test_id_component(self, driver, settings, config):

        """
               Rename this test function and fill in the appropriate information.
               :param driver: A Driver object, connected to one Device, use the the getter methods to fetch related objects.
               :settings: A Settings object
               :param config: A configparser object containing all the key-value pair from config.ini file.
               :return: Void
               """
        logging.debug("Starting test %s on device %s", "MapPanel", driver.getDevice().getName())

        try:

            driver.actions.UpdateTestName(__file__, driver.getDevice().getName(),
                                          driver.webdriver.session_id)
            userProfileDownload = True
            login_data = {}

            login_data[config['STRINGS']['USER_PROFILE_DOWNLOAD']] = userProfileDownload
            login_data[config['STRINGS']['SERVER_URI']] = config['DEFAULT']['SERVER']
            login_data[config['STRINGS']['USERNAME']] = "test-account"

            settings.LoginWithSettings(login_data)

            driver.actions.SwitchToWebView()

            contentPage = qmcauto.objectrepo.ui.ContentPage.ContentPage(1, driver, driver.getDevice())
            contentPage.openContentPageMenu()
            contentPage.checkLabels()






        except Exception as e:

            logging.error(str(e))
            driver.ReportResults(str(e))
            raise





        finally:

            driver.deinitialize()