import binascii, base64, hashlib, argparse, logging
from Cryptodome import Random
from .BrowserClient import BrowserClient
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

# Use this function to add the minimum required args to your login flow
def get_default_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="argparser")
    parser.add_argument('--user', help='Your MitID username. For example: "GenericDanishCitizen"', required=True)
    parser.add_argument('--password', help='Your MitID password for use with the "TOKEN" login method. For example: "CorrectHorseBatteryStaple"', required=False)
    parser.add_argument('--method', choices=['APP', 'TOKEN'], help='Which method to use when logging in to MitID, default APP', default='APP', required=False)
    parser.add_argument('--proxy', help='An optional socks5 proxy to use for all communication with MitID', required=False)
    return parser

# Use this function to process the minimum required args for your login flow
def process_args(args):
    method = args.method
    user_id = args.user
    if args.password and args.method == 'TOKEN':
        password = args.password
    elif args.method == 'TOKEN':
        raise ValueError("Password is required for TOKEN authentication method")
    else:
        password = None
    return method, user_id, password, args.proxy

# get_authentication_code is generally generic enough that you do not need to create your own
# calls to BrowserClient
def get_authentication_code(session, aux, method, user_id, password):
    client_hash = binascii.hexlify(base64.b64decode(aux["coreClient"]["checksum"])).decode('ascii')
    authentication_session_id = aux["parameters"]["authenticationSessionId"]

    MitIDClient = BrowserClient(client_hash, authentication_session_id, session)
    available_authenticators = MitIDClient.identify_as_user_and_get_available_authenticators(user_id)

    _LOGGER.debug(f"Available authenticator: {available_authenticators}")

    if method == "TOKEN" and "TOKEN" in available_authenticators:
        if not password:
            raise ValueError("Password is required for TOKEN authentication")
        # Token digits must be provided via the caller, not via interactive input
        raise NotImplementedError(
            "TOKEN authentication requires token_digits parameter - interactive input not supported"
        )
    elif method == "APP" and "APP" in available_authenticators:
        MitIDClient.authenticate_with_app()
    elif method == "TOKEN" and "TOKEN" not in available_authenticators:
        raise Exception(f"Token authentication method chosen but not available for MitID user")
    elif method == "APP" and "APP" not in available_authenticators:    
        raise Exception(f"App authentication method chosen but not available for MitID user")
    else:
        raise Exception(f"Unknown authenticator method: {method}")

    authorization_code = MitIDClient.finalize_authentication_and_get_authorization_code()
    return authorization_code

def choose_between_multiple_identitites(session, request, soup, identity_index=0):
    """Choose between multiple identities.

    Args:
        session: requests session
        request: current request object
        soup: BeautifulSoup parsed response
        identity_index: zero-based index of the identity to select (default: 0, first identity)

    Returns:
        Tuple of (request, soup) after identity selection
    """
    data = {}
    for soup_input in soup.form.select("input"):
        try:
            data[soup_input["name"]] = soup_input["value"]
        except KeyError:
            data[soup_input.get("name", "")] = ""
    login_options = soup.select("div.list-link-box")
    _LOGGER.info('Multiple identities available:')
    for i, login_option in enumerate(login_options):
        _LOGGER.info(f'{i+1}: {login_option.select_one("div.list-link-text").string}')

    if identity_index < 0 or identity_index >= len(login_options):
        raise ValueError(f"Identity index {identity_index} out of range (0-{len(login_options)-1})")

    selected_option = login_options[identity_index].a["data-loginoptions"]
    data["ChosenOptionJson"] = selected_option
    _LOGGER.info(f'Selected identity {identity_index + 1}')

    request = session.post(request.url, data=data)
    soup = BeautifulSoup(request.text, "xml")
    return request, soup

def __generate_random_string():
    return binascii.hexlify(Random.new().read(28)).decode("utf-8")

def __generate_challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")

# Use this function to generate the default parameters for nem_login flows
def generate_nem_login_parameters():
    nem_login_state = __generate_random_string()
    nem_login_nonce = __generate_random_string()
    nem_login_code_verifier = __generate_random_string()
    nem_login_code_challenge = __generate_challenge(nem_login_code_verifier)

    return nem_login_state, nem_login_nonce, nem_login_code_verifier, nem_login_code_challenge
