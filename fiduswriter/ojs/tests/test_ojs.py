import time
import json
import multiprocessing
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi
import socket
import requests
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException
from testing.testcases import LiveTornadoTestCase
from testing.selenium_helper import SeleniumHelper


# From https://realpython.com/testing-third-party-apis-with-mock-servers/
class MockServerRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not (
            '/index.php/index/gateway'
            '/plugin/FidusWriterGatewayPlugin/'
        ) in self.path:
            self.send_response(requests.codes.not_found)
            self.end_headers()
            return
        url_parts = self.path.split('/FidusWriterGatewayPlugin/')[1].split('?')
        relative_url = url_parts[0]
        query = url_parts[1]
        if 'key=OJS_KEY' not in query:
            self.send_response(requests.codes.not_found)
            self.end_headers()
            return
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': self.headers['Content-Type'],
            }
        )
        if relative_url == 'authorSubmit':
            if all(i in form for i in (
                "username",
                "title",
                "abstract",
                "first_name",
                "last_name",
                "email",
                "journal_id",
                "fidus_url",
                "version"
            )):
                self.send_response(requests.codes.ok)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'submission_id': 15,
                    'user_id': 8979
                }).encode(encoding='utf_8'))
        elif relative_url == 'reviewerSubmit':
            if all(i in form for i in (
                "submission_id",
                "version",
                "user_id",
                "editor_message",
                "editor_author_message",
                "recommendation"
            )):
                self.send_response(requests.codes.ok)
                self.end_headers()
        else:
            self.send_response(requests.codes.not_found)
            self.end_headers()
        return

    def do_GET(self):
        if (
            '/index.php/index/gateway'
            '/plugin/FidusWriterGatewayPlugin/'
        ) not in self.path:
            self.send_response(requests.codes.not_found)
            self.end_headers()
            return
        url_parts = self.path.split('/FidusWriterGatewayPlugin/')[1].split('?')
        relative_url = url_parts[0]
        query = url_parts[1]
        if 'key=OJS_KEY' not in query:
            self.send_response(requests.codes.not_found)
            self.end_headers()
            return
        if relative_url == 'journals':
            self.send_response(requests.codes.ok)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'journals': [
                    {
                        'id': 4,
                        'name': 'Journal of Progress',
                        'contact_email': 'contact@progress.com',
                        'contact_name': 'John B. Future',
                        'url_relative_path': 'future/',
                        'description': 'A future journal'
                    },
                    {
                        'id': 5,
                        'name': 'Journal of the Past',
                        'contact_email': 'contact@goodolddays.com',
                        'contact_name': 'Remember Falls',
                        'url_relative_path': 'past/',
                        'description': 'A historic journal'
                    },
                ],
            }).encode(encoding='utf_8'))
        else:
            self.send_response(requests.codes.not_found)
            self.end_headers()
        return


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


class OJSDummyTest(LiveTornadoTestCase, SeleniumHelper):
    fixtures = [
        'initial_documenttemplates.json',
        'initial_styles.json'
    ]

    @classmethod
    def start_server(cls, port):
        httpd = HTTPServer(('', port), MockServerRequestHandler)
        httpd.serve_forever()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_url = cls.live_server_url
        driver_data = cls.get_drivers(1)
        cls.driver = driver_data["drivers"][0]
        cls.client = driver_data["clients"][0]
        cls.driver.implicitly_wait(driver_data["wait_time"])
        cls.wait_time = driver_data["wait_time"]
        cls.server_port = get_free_port()
        cls.server = multiprocessing.Process(
            target=cls.start_server,
            args=(cls.server_port,)
        )
        cls.server.daemon = True
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server.terminate()
        super().tearDownClass()

    def setUp(self):
        self.admin = self.create_user(
            username='Admin',
            email='admin@admin.com',
            passtext='password'
        )
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()
        self.user1 = self.create_user(
            username='User1',
            email='user1@user.com',
            passtext='password'
        )
        self.editor1 = self.create_user(
            username='Editor1',
            email='editor1@user.com',
            passtext='password'
        )
        self.editor2 = self.create_user(
            username='Editor2',
            email='editor2@user.com',
            passtext='password'
        )

    def tearDown(self):
        self.admin.delete()
        self.user1.delete()

    def assertSuccessAlert(self, message):
        i = 0
        message_found = False
        while(i < 100):
            i = i + 1
            try:
                if self.driver.find_element(
                    By.CSS_SELECTOR,
                    "body #alerts-outer-wrapper .alerts-success"
                ).text == message:
                    message_found = True
                    break
                else:
                    time.sleep(0.1)
                    continue
            except StaleElementReferenceException:
                time.sleep(0.1)
                continue
        self.assertTrue(message_found)

    def test_ojs_dummy(self):
        # Register journals
        self.login_user(self.admin, self.driver, self.client)
        self.driver.get(urljoin(self.base_url, "/admin/"))
        self.driver.find_element(
            By.CSS_SELECTOR,
            'a[href="/admin/ojs/journal/"]'
        ).click()
        self.driver.find_element(
            By.CSS_SELECTOR,
            'a[href="register_journal/"]'
        ).click()
        self.driver.find_element_by_id(
            'ojs_url'
        ).send_keys('http://localhost:{}/'.format(self.server_port))
        self.driver.find_element_by_id(
            'ojs_key'
        ).send_keys('OJS_KEY')
        self.driver.find_element_by_id(
            'get_journals'
        ).click()
        self.driver.find_element_by_id(
            'editor_4'
        ).send_keys(self.editor1.id)
        self.driver.find_element(
            By.CSS_SELECTOR,
            'button[data-id="4"]'
        ).click()
        self.driver.find_element_by_id(
            'editor_5'
        ).send_keys(self.editor2.id)
        self.driver.find_element(
            By.CSS_SELECTOR,
            'button[data-id="5"]'
        ).click()
        # Register journals with templates
        # Log in as user to submit an article
        self.login_user(self.user1, self.driver, self.client)
        self.driver.get(urljoin(self.base_url, "/"))
        WebDriverWait(self.driver, self.wait_time).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    ".new_document button"
                )
            )
        ).click()
        WebDriverWait(self.driver, self.wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'editor-toolbar'))
        )
        self.driver.find_element(By.CSS_SELECTOR, ".article-title").click()
        self.driver.find_element(By.CSS_SELECTOR, ".article-title").send_keys(
            "Test"
        )
        # We enable the abstract
        self.driver.find_element(
            By.CSS_SELECTOR,
            "#header-navigation > div:nth-child(3) > span"
        ).click()
        self.driver.find_element(
            By.CSS_SELECTOR,
            (
                "#header-navigation > div:nth-child(3) > div "
                "> ul > li:nth-child(1) > span"
            )
        ).click()
        self.driver.find_element(
            By.CSS_SELECTOR,
            (
                "#header-navigation > div:nth-child(3) > div "
                "> ul > li:nth-child(1) > div > ul > li:nth-child(3) > span"
            )
        ).click()
        self.driver.find_element(By.CSS_SELECTOR, ".article-body").click()
        ActionChains(self.driver).send_keys(
            Keys.LEFT
        ).send_keys(
            "An abstract title"
        ).perform()
        self.driver.find_element_by_xpath(
            '//*[@id="header-navigation"]/div[1]/span'
        ).click()
        self.driver.find_element_by_xpath(
            '//*[normalize-space()="Submit to journal"]'
        ).click()
        self.driver.find_element_by_id(
            'submission-journal'
        ).click()
        self.driver.find_element_by_xpath(
            '//*[normalize-space()="Journal of the Past"]'
        ).click()
        self.assertEqual(
            self.driver.find_element_by_id(
                'submission-abstract'
            ).get_attribute('value'),
            'An abstract title'
        )
        self.driver.find_element_by_id(
            'submission-firstname'
        ).send_keys('Jens')
        self.driver.find_element_by_id(
            'submission-lastname'
        ).send_keys('Hansen')
        self.driver.find_element_by_xpath(
            '//*[normalize-space()="Submit"]'
        ).click()
        self.assertSuccessAlert("Article submitted")
