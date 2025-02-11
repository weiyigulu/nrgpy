try:
    from nrgpy import logger
except ImportError:
    pass
from nrgpy import token_file
import base64
from datetime import datetime, timedelta
import json
import pickle
import requests
import traceback

url_base = "https://cloud-api.nrgsystems.com/nrgcloudcustomerapi/"
token_url = url_base + "token"
convert_url = url_base + "data/convert"
export_url = url_base + "data/export"
create_export_job_url = url_base + "data/createexportjob"
export_job_url = url_base + "data/exportjob"
import_url = url_base + "data/import"
sites_url = url_base + "sites"


class cloud_api(object):
    """
    Parent class for NRG Cloud API functionality

    nrgpy simplifies usage of the NRG Cloud APIs. See the documentation for the
    cloud_api.sites, .export, and .convert modules for more information.

    For non-nrgpy implementations, the following Usage information may be
    helpful.

    The base url for the NRG Cloud APIs is

    https://cloud-api.nrgsystems.com/nrgcloudcustomerapi/

    Use client ID and secret to obtain a bearer token at the /token endpoint.
    This token is good for 24 hours.

    You will be limited to creating 10 tokens per day, though normally one
    token should suffice, so please cache. nrgpy's cloud_api modules will
    automatically manage bearer tokens, refreshing only when necessary.

    Endpoints:

    base
        https://cloud-api.nrgsystems.com/nrgcloudcustomerapi/
    /token
        for accessing bearer token. Client ID and Secret required.
    /sites
        Get list of sites. Bearer token required
    /convert
        Convert RLD file to TXT. Bearer token required
    /export
        Export TXT or RLD files for a given date range. NEC files may be used
        to format TXT outputs. Bearer  token required.
    """

    def __init__(self, client_id="", client_secret=""):
        logger.debug(f"cloud base: {url_base}")
        self.client_id = client_id
        self.client_secret = client_secret

        if self.client_id and self.client_secret:
            self.maintain_session_token()
        else:
            print(
                "[Access error] Valid credentials are required.\n\nPlease visit https://cloud.nrgsystems.com/data-manager/api-setup\nto access your API credentials"
            )
            logger.error(
                "[Access error] Valid credentials are required. Please visit https://cloud.nrgsystems.com/data-manager/api-setup to access your API credentials"
            )

    def request_session_token(self):
        """Generates a new session token for convert service api

        Requires an active account with NRG Cloud. To sign
        up for a free account, go to:

        https://cloud.nrgsystems.com

        Client ID and Secret can be accessed here:

        https://cloud.nrgsystems.com/data-manager/api-setup


        Parameters
        ----------
        client_id : str
            obtained from NRG Systems
        client_secret : str

        Returns
        -------
        session_token : str
            valid for 24 hour
        session_start_time : datetime
            start time of 24 hour countdown
        """
        logger.debug("session token requested")
        print(
            "{} | Requesting session token ... ".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            end="",
            flush=True,
        )

        request_token_header = {"content-type": "application/json"}
        request_payload = {
            "clientId": "{}".format(self.client_id),
            "clientSecret": "{}".format(self.client_secret),
        }

        self.resp = requests.post(
            data=json.dumps(request_payload),
            headers=request_token_header,
            url=token_url,
        )
        self.session_start_time = datetime.now()

        if self.resp.status_code == 200:
            print("[OK]")
            logger.info("new session token OK")
            self.session_token = json.loads(self.resp.text)["apiToken"]
        else:
            logger.error("unable to get session token")
            logger.debug(f"{self.resp.text}")
            print("[FAILED] | unable to get session token.")
            self.session_token = False

    def token_valid(self):
        """check if token is still valid

        Parameters
        ----------
        session_start_time : datetime
            generated at time of token request

        Returns
        -------
        status : bool
            true if still valid, false if expired
        """
        if datetime.now() < self.session_start_time + timedelta(hours=22):
            if self.session_token is not False:
                # logger.debug(f"session token reused: expires {self.session_start_time + timedelta(hours=24)}")
                return True

        return False

    def save_token(self, filename=token_file):
        """save session token in token pickle file"""
        with open(filename, "wb") as f:
            pickle.dump([self.session_token, self.session_start_time], f)

    def load_token(self, filename=token_file):
        """read session token from pickle file"""
        with open(filename, "rb") as f:
            self.session_token, self.session_start_time = pickle.load(f)

    def maintain_session_token(self, filename=token_file):
        """maintain a current/valid session token for data service api"""
        try:
            self.load_token(filename=token_file)
            if not self.token_valid():
                self.request_session_token()
                self.save_token()
        except:
            self.request_session_token()
            self.save_token()

    def prepare_file_bytes(self, filename=""):
        file_bytes = base64.encodebytes(open(filename, "rb").read())
        return file_bytes


def is_authorized(resp):
    if resp.status_code == 401 or resp.status_code == 400:
        try:
            logger.error(json.loads(resp.text)["apiResponseMessage"])
            print(json.loads(resp.text)["apiResponseMessage"])
        except:
            logger.error("Unable to process request")
            logger.debug(traceback.format_exc())
            print("Unable to complete request.  Check nrpy log file for details")
        return False

    return True
