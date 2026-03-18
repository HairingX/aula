# MitID Authentication for Aula

## Overview

The `aula_login_client` package handles authentication with Aula via Denmark's MitID national identity system. It replaces the legacy UniLogin username/password flow with a full OAuth 2.0 + SAML + MitID authentication chain, matching the flow used by the official Aula mobile app.

## Dependencies

Added to `manifest.json` requirements:

| Package | Purpose |
|---------|---------|
| `pycryptodomex` | AES-GCM encryption for MitID's SRP (Secure Remote Password) protocol. Used during the cryptographic handshake when authenticating with the MitID app or code token. |
| `qrcode` | Generates QR codes that users scan with the MitID app. The MitID server may return either a QR code challenge or an OTP code — both paths are supported. |
| `beautifulsoup4` | Already present. Used to parse HTML responses during the SAML redirect chain. |
| `lxml` | Already present. HTML parser backend for BeautifulSoup. |

Note: `requests` is provided by Home Assistant core and is not listed in requirements.

## Package Structure

```
aula_login_client/
├── __init__.py                  # Exports AulaLoginClient and exceptions
├── client.py                    # Main client — orchestrates the full auth flow
├── exceptions.py                # Exception hierarchy
└── mitid_browserclient/         # MitID protocol implementation (upstream)
    ├── __init__.py
    ├── BrowserClient.py         # MitID session management, app/token auth, QR codes
    ├── CustomSRP.py             # SRP-6a protocol + AES-GCM encrypt/decrypt
    ├── Helpers.py               # Utility functions for MitID flows
    └── login_flows/
        ├── __init__.py
        └── aula.py              # Placeholder (flow logic lives in client.py)
```

## Authentication Flow

The complete flow involves 8 steps across 4 identity providers:

```
Aula (OAuth 2.0/PKCE)
  → login.aula.dk (SAML SP)
    → broker.unilogin.dk (SAML IdP broker)
      → nemlog-in.mitid.dk (NemLog-in)
        → mitid.dk (MitID core)
```

### Step-by-step

#### Step 1: Start OAuth 2.0 flow
`AulaLoginClient.step1_start_oauth_flow()`

- Generates PKCE parameters (`code_verifier` + `code_challenge`)
- Generates random `state` parameter
- Sends GET to `login.aula.dk/simplesaml/module.php/oidc/authorize.php`
- Uses Aula's mobile app `client_id` and `scope: aula-sensitive`
- Returns: redirect URL to SAML chain

#### Step 2: Follow redirect chain to MitID
`AulaLoginClient.step3_follow_redirect_chain()`

- Follows up to 10 HTTP redirects through:
  - `login.aula.dk` → `broker.unilogin.dk` → `nemlog-in.mitid.dk`
- At the broker page, selects NemLogin3 (MitID) as identity provider
- Returns: `__RequestVerificationToken` from the MitID page

#### Step 3: MitID authentication
`AulaLoginClient.step4_mitid_authentication()`

- POSTs to `nemlog-in.mitid.dk/login/mitid/initialize` with the verification token
- Receives `Aux` JSON payload containing MitID session parameters
- Creates a `BrowserClient` instance with the MitID session
- Identifies the user and discovers available authenticators

Then one of two authentication methods:

**APP method** (MitID app):
1. `BrowserClient.authenticate_with_app()` — starts app authentication
2. Polls `mitid.dk` for user action
3. Server returns either:
   - `channel_validation_otp` → display OTP code for user to enter in MitID app
   - `channel_validation_tqr` → generate alternating QR codes for user to scan
4. After user approves in the app → `channel_verified` → `OK`
5. Completes SRP-6a cryptographic handshake (stage 1/3/5)
6. Submits flow value proof (HMAC-SHA256 over session parameters)

**TOKEN method** (code token device + password):
1. `BrowserClient.authenticate_with_token(digits)` — submits 6-digit code from physical token
2. SRP handshake with token-derived password
3. `BrowserClient.authenticate_with_password(password)` — submits MitID password
4. SRP handshake with PBKDF2-derived password (20,000 iterations SHA-256)

Returns: MitID authorization code

#### Step 4: Complete MitID flow
`AulaLoginClient.step5_complete_mitid_flow()`

- POSTs MitID authorization code back to `nemlog-in.mitid.dk/login/mitid`
- Handles multiple-identity selection if user has more than one NemLog-in identity
- Returns: SAML response (`SAMLResponse` + `RelayState`)

#### Step 5: SAML broker flow
`AulaLoginClient.step6_saml_broker_flow()`

- POSTs SAML response to `broker.unilogin.dk/.../nemlogin3/endpoint`
- Follows broker redirect chain
- Handles post-broker-login confirmation page (role selection: Kontakt/Elev)
- Returns: final SAML response for Aula

#### Step 6: Complete Aula login
`AulaLoginClient.step7_complete_aula_login()`

- POSTs final SAML response to `login.aula.dk/simplesaml/.../saml2-acs.php/uni-sp`
- Follows redirect chain back to the OAuth callback URL
- Returns: callback URL containing OAuth authorization `code`

#### Step 7: Exchange OAuth code for tokens
`AulaLoginClient.step8_exchange_oauth_code()`

- POSTs to `login.aula.dk/simplesaml/module.php/oidc/token.php`
- Exchanges authorization code + PKCE `code_verifier` for tokens
- Returns: `access_token`, `refresh_token`, `expires_in`, `expires_at`

#### Step 8: Test API access
`AulaLoginClient.step9_test_api_access()`

- Tests token validity against Aula v22 API endpoints
- Returns: profile data and endpoint availability

## Authentication Methods

### APP (recommended for Home Assistant)
- User approves login in the MitID mobile app
- Supports both OTP code display and QR code scanning
- No credentials stored beyond the MitID username

### TOKEN (code token + password)
- Requires a physical MitID code token device
- User provides 6-digit code from the device + their MitID password
- Both `mitid_password` and `mitid_token` (6 digits) must be provided at authentication time

## Token Management

### Token lifecycle
- Access tokens have a limited lifetime (typically ~3600 seconds)
- The client tracks `expires_at` timestamps
- `renew_access_token()` uses the refresh token to obtain new access tokens
- `check_token_expiration()` decodes the JWT to check remaining validity
- `test_token_validity()` makes an actual API call to verify the token works

### Token renewal
When calling `renew_access_token()`:
1. POSTs refresh token to the token endpoint
2. Updates `access_token`, `refresh_token` (if rotated), `expires_in`, and `expires_at`
3. Returns `True` on success, `False` on failure

## SRP Protocol (Secure Remote Password)

The MitID authentication uses SRP-6a, implemented in `CustomSRP.py`:

1. **Stage 1**: Client generates random `a`, computes `A = g^a mod N` (768-hex-char public value)
2. **Stage 3**: Client receives server's `B` and `srpSalt`, computes session key `K` and proof `M1`
3. **Stage 5**: Client verifies server's proof `M2` (mutual authentication)
4. **AuthEnc/AuthDec**: AES-256-GCM encryption using session key `K` for response signature verification

The 3072-bit prime `N` and generator `g=2` are hardcoded per the MitID specification.

## Error Handling

Exception hierarchy:
```
AulaAuthenticationError (base)
├── MitIDError          — MitID protocol failures
├── TokenExpiredError   — Access token expired
├── APIError            — API access failures
├── ConfigurationError  — Setup/dependency issues
├── NetworkError        — HTTP/connection failures
├── SAMLError           — SAML redirect chain failures
└── OAuthError          — OAuth protocol failures
```

## Security Considerations

- No credentials are persisted — MitID username is stored in config, but passwords/tokens are ephemeral
- PKCE (Proof Key for Code Exchange) prevents authorization code interception
- SRP protocol ensures passwords never travel over the wire in plaintext
- All HTTP calls use timeouts (default 30s) to prevent hanging
- Sensitive values (passwords, tokens) are not logged
- The `requests.Session` is not shared as a mutable default argument
