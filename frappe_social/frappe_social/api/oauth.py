"""
OAuth API Endpoints for Frappe Social Media Scheduler

Handles OAuth flow for all platforms:
- Facebook/Instagram (Meta Graph API)
- LinkedIn, Twitter, YouTube
"""

import frappe
import secrets
import hashlib
import base64
import requests
from frappe import _
from frappe.utils import get_url, now_datetime, add_to_date


# =============================================================================
# OAuth Initiation
# =============================================================================


@frappe.whitelist()
def initiate_oauth(
    platform: str, account_name: str = None, account_description: str = None, organization: str = None
) -> dict:
    """Start OAuth flow for a platform"""
    state = secrets.token_urlsafe(32)
    cache_data = {
        "platform": platform,
        "account_name": account_name,
        "account_description": account_description,
        "organization": organization,
        "user": frappe.session.user,
    }
    redirect_uri = get_callback_url(platform)
    settings = frappe.get_single("Social Settings")

    auth_url = _get_auth_url(platform, settings, redirect_uri, state)
    frappe.cache().set_value(f"oauth_state_{state}", cache_data, expires_in_sec=600)

    return {"authorization_url": auth_url, "state": state}


def get_callback_url(platform: str) -> str:
    return f"{get_url()}/api/method/frappe_social.frappe_social.api.oauth.callback_{platform.lower()}"


def _get_auth_url(platform: str, settings, redirect_uri: str, state: str) -> str:
    """Build OAuth authorization URL"""
    if platform == "Twitter":
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
        )
        frappe.cache().set_value(
            f"twitter_verifier_{state}",
            code_verifier,
            expires_in_sec=600,
        )
        params = {
            "response_type": "code",
            "client_id": settings.twitter_client_id,
            "redirect_uri": redirect_uri,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"https://twitter.com/i/oauth2/authorize?{'&'.join(f'{k}={frappe.utils.quoted(str(v))}' for k,v in params.items())}"

    elif platform == "LinkedIn":
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "openid profile email w_member_social r_organization_admin w_organization_social",
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{'&'.join(f'{k}={frappe.utils.quoted(str(v))}' for k,v in params.items())}"

    elif platform in ["Instagram", "Facebook"]:
        scopes = [
            "pages_show_list",
            "pages_read_engagement",
            "pages_manage_posts",
            "pages_read_user_content",
            "business_management",
            "email",
            "public_profile",
            "ads_management",
            "ads_read",
        ]
        if platform == "Instagram":
            scopes.extend(["instagram_basic", "instagram_content_publish", "instagram_manage_insights"])
        params = {
            "client_id": settings.meta_app_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "state": state,
            "response_type": "code",
        }
        return f"https://www.facebook.com/v24.0/dialog/oauth?{'&'.join(f'{k}={frappe.utils.quoted(str(v))}' for k,v in params.items())}"

    elif platform == "YouTube":
        params = {
            "client_id": settings.youtube_client_id,
            "redirect_uri": redirect_uri,
            "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email",
            "state": state,
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{'&'.join(f'{k}={frappe.utils.quoted(str(v))}' for k,v in params.items())}"

    frappe.throw(_(f"Unknown platform: {platform}"))


# =============================================================================
# OAuth Callbacks
# =============================================================================


@frappe.whitelist(allow_guest=True)
def callback_twitter():
    code, state, error = (
        frappe.request.args.get("code"),
        frappe.request.args.get("state"),
        frappe.request.args.get("error"),
    )
    if error:
        return _oauth_error_redirect(f"Twitter: {error}")

    cache_data = frappe.cache().get_value(f"oauth_state_{state}")
    code_verifier = frappe.cache().get_value(f"twitter_verifier_{state}")
    if not cache_data or cache_data.get("platform") != "Twitter" or not code_verifier:
        return _oauth_error_redirect("Invalid OAuth state")

    settings = frappe.get_single("Social Settings")
    response = requests.post(
        "https://api.twitter.com/2/oauth2/token",
        data={
            "code": code,
            "grant_type": "authorization_code",
            "client_id": settings.twitter_client_id,
            "redirect_uri": get_callback_url("Twitter"),
            "code_verifier": code_verifier,
        },
        auth=(settings.twitter_client_id, settings.get_password("twitter_client_secret")),
    )

    if response.status_code != 200:
        return _oauth_error_redirect(f"Token exchange failed: {response.text}")

    token_data = response.json()
    user_response = requests.get(
        "https://api.twitter.com/2/users/me",
        params={"user.fields": "profile_image_url,public_metrics"},
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    user_data = user_response.json().get("data", {})

    frappe.set_user(cache_data["user"])
    integration = _save_integration(
        platform="Twitter",
        profile_id=user_data.get("id"),
        profile_name=user_data.get("username"),
        profile_image=user_data.get("profile_image"),
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 7200),
        account_type="Personal",
        account_name=cache_data.get("account_name"),
        account_description=cache_data.get("account_description"),
        organization=cache_data.get("organization"),
    )

    frappe.cache().delete_value(f"oauth_state_{state}")
    frappe.cache().delete_value(f"twitter_verifier_{state}")
    return _oauth_success_redirect(integration.name)


@frappe.whitelist(allow_guest=True)
def callback_linkedin():
    code, state, error = (
        frappe.request.args.get("code"),
        frappe.request.args.get("state"),
        frappe.request.args.get("error"),
    )
    if error:
        return _oauth_error_redirect(f"LinkedIn: {error}")

    cache_data = frappe.cache().get_value(f"oauth_state_{state}")
    if not cache_data or cache_data.get("platform") != "LinkedIn":
        return _oauth_error_redirect("Invalid OAuth state")

    settings = frappe.get_single("Social Settings")
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            # "redirect_uri": get_callback_url("LinkedIn"),
            "client_id": settings.linkedin_client_id,
            "client_secret": settings.get_password("linkedin_client_secret"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if response.status_code != 200:
        return _oauth_error_redirect(f"Token exchange failed: {response.text}")

    token_data = response.json()
    user_data = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    ).json()

    frappe.set_user(cache_data["user"])
    integration = _save_integration(
        platform="LinkedIn",
        profile_id=user_data.get("sub"),
        profile_name=user_data.get("name"),
        profile_image=user_data.get("picture"),
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 5184000),
        account_type="Personal",
        account_name=cache_data.get("account_name"),
        account_description=cache_data.get("account_description"),
        organization=cache_data.get("organization"),
    )

    frappe.cache().delete_value(f"oauth_state_{state}")
    return _oauth_success_redirect(integration.name)


# =============================================================================
# Meta (Facebook/Instagram) Handler
# =============================================================================


@frappe.whitelist(allow_guest=True)
def callback_facebook():
    return _handle_meta_callback("Facebook")


@frappe.whitelist(allow_guest=True)
def callback_instagram():
    return _handle_meta_callback("Instagram")


def _handle_meta_callback(platform: str):
    """Handle Facebook/Instagram OAuth callback"""
    code, state, error = (
        frappe.request.args.get("code"),
        frappe.request.args.get("state"),
        frappe.request.args.get("error"),
    )
    if error:
        return _oauth_error_redirect(f"{platform}: {error}")

    cache_data = frappe.cache().get_value(f"oauth_state_{state}")
    if not cache_data or cache_data.get("platform") != platform:
        return _oauth_error_redirect("Invalid OAuth state")

    settings = frappe.get_single("Social Settings")
    api_version = settings.meta_api_version or "v21.0"

    # Get long-lived token
    short_token = (
        requests.get(
            f"https://graph.facebook.com/{api_version}/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.get_password("meta_app_secret"),
                "redirect_uri": get_callback_url(platform),
                "code": code,
            },
        )
        .json()
        .get("access_token")
    )

    long_token_data = requests.get(
        f"https://graph.facebook.com/{api_version}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.meta_app_id,
            "client_secret": settings.get_password("meta_app_secret"),
            "fb_exchange_token": short_token,
        },
    ).json()

    user_token = long_token_data.get("access_token", short_token)
    expires_in = long_token_data.get("expires_in", 5184000)

    # Get user info
    me_data = requests.get(
        f"https://graph.facebook.com/{api_version}/me",
        params={"access_token": user_token, "fields": "id,name,email"},
    ).json()

    # Get pages
    pages = (
        requests.get(
            f"https://graph.facebook.com/{api_version}/me/accounts",
            params={"access_token": user_token, "fields": "id,name,access_token,picture{url},fan_count"},
        )
        .json()
        .get("data", [])
    )

    if not pages:
        return _oauth_error_redirect("No Facebook Pages found. Create a Page first.")

    # For Instagram, get linked IG accounts
    if platform == "Instagram":
        ig_pages = []
        for page in pages:
            ig_data = requests.get(
                f"https://graph.facebook.com/{api_version}/{page['id']}",
                params={
                    "access_token": page["access_token"],
                    "fields": "instagram_business_account{id,username,profile_picture_url,followers_count}",
                },
            ).json()
            if ig_data.get("instagram_business_account"):
                ig = ig_data["instagram_business_account"]
                ig_pages.append(
                    {
                        "page_id": page["id"],
                        "page_access_token": page["access_token"],
                        "instagram_id": ig["id"],
                        "instagram_username": ig.get("username", ""),
                        "followers_count": ig.get("followers_count", 0),
                    }
                )
        if not ig_pages:
            return _oauth_error_redirect("No Instagram Business accounts found.")
        pages = ig_pages

    # Store session for page selection
    session_key = secrets.token_urlsafe(32)
    frappe.cache().set_value(
        f"meta_pages_{session_key}",
        {
            "platform": platform,
            "user": cache_data["user"],
            "user_access_token": user_token,
            "expires_in": expires_in,
            "pages": pages,
            "auth_user_id": me_data.get("id"),
            "auth_user_name": me_data.get("name"),
            "account_name": cache_data.get("account_name"),
            "account_description": cache_data.get("account_description"),
            "organization": cache_data.get("organization"),
        },
        expires_in_sec=600,
    )

    frappe.cache().delete_value(f"oauth_state_{state}")

    # Single page - connect directly
    if len(pages) == 1:
        frappe.set_user(cache_data["user"])
        return _connect_meta_page(session_key, 0)

    # Multiple pages - redirect to selection
    frappe.local.response.update(
        {"type": "redirect", "location": f"/select-social-page?session={session_key}&platform={platform}"}
    )


@frappe.whitelist()
def get_available_pages(session_key: str) -> dict:
    """Get pages for selection UI"""
    cache_data = frappe.cache().get_value(f"meta_pages_{session_key}")
    if not cache_data or cache_data["user"] != frappe.session.user:
        frappe.throw(_("Session expired"))

    platform = cache_data["platform"]
    formatted = []
    for i, page in enumerate(cache_data["pages"]):
        if platform == "Instagram":
            formatted.append(
                {
                    "index": i,
                    "id": page["instagram_id"],
                    "name": f"@{page['instagram_username']}",
                    "followers": page.get("followers_count", 0),
                }
            )
        else:
            formatted.append(
                {"index": i, "id": page["id"], "name": page["name"], "followers": page.get("fan_count", 0)}
            )

    return {"platform": platform, "pages": formatted}


@frappe.whitelist()
def connect_page(session_key: str, page_index: int) -> dict:
    return _connect_meta_page(session_key, int(page_index))


def _connect_meta_page(session_key: str, page_index: int):
    """Connect a specific Meta page"""
    cache_data = frappe.cache().get_value(f"meta_pages_{session_key}")
    if not cache_data:
        frappe.throw(_("Session expired"))

    page = cache_data["pages"][page_index]
    platform = cache_data["platform"]

    if platform == "Instagram":
        profile_id, profile_name = page["instagram_id"], page["instagram_username"]
        page_id, page_token = page["page_id"], page["page_access_token"]
        account_type, followers = "Business", page.get("followers_count", 0)
    else:
        profile_id, profile_name = page["id"], page["name"]
        page_id, page_token = page["id"], page["access_token"]
        account_type, followers = "Page", page.get("fan_count", 0)

    integration = _save_integration(
        platform=platform,
        profile_id=profile_id,
        profile_name=profile_name,
        profile_image=page.get("picture", {}).get("data", {}).get("url"),
        access_token=cache_data["user_access_token"],
        expires_in=cache_data["expires_in"],
        page_id=page_id,
        page_access_token=page_token,
        account_type=account_type,
        followers_count=followers,
        account_name=cache_data.get("account_name"),
        account_description=cache_data.get("account_description"),
        organization=cache_data.get("organization"),
    )

    return _oauth_success_redirect(integration.name)


@frappe.whitelist(allow_guest=True)
def callback_youtube():
    code, state, error = (
        frappe.request.args.get("code"),
        frappe.request.args.get("state"),
        frappe.request.args.get("error"),
    )
    if error:
        return _oauth_error_redirect(f"YouTube: {error}")

    cache_data = frappe.cache().get_value(f"oauth_state_{state}")
    if not cache_data or cache_data.get("platform") != "YouTube":
        return _oauth_error_redirect("Invalid OAuth state")

    settings = frappe.get_single("Social Settings")
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.youtube_client_id,
            "client_secret": settings.get_password("youtube_client_secret"),
            "redirect_uri": get_callback_url("YouTube"),
            "grant_type": "authorization_code",
        },
    )

    if response.status_code != 200:
        return _oauth_error_redirect(f"Token exchange failed: {response.text}")

    token_data = response.json()
    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    ).json()

    channel_data = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"access_token": token_data["access_token"], "part": "snippet,statistics", "mine": "true"},
    ).json()
    channels = channel_data.get("items", [])

    if not channels:
        return _oauth_error_redirect("No YouTube channel found")

    channel = channels[0]
    snippet, stats = channel.get("snippet", {}), channel.get("statistics", {})

    frappe.set_user(cache_data["user"])
    integration = _save_integration(
        platform="YouTube",
        profile_id=channel["id"],
        profile_name=snippet.get("title"),
        profile_image=snippet.get("thumbnails", {}).get("high", {}).get("url"),
        access_token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 3600),
        account_type="Channel",
        followers_count=int(stats.get("subscriberCount", 0)),
        account_name=cache_data.get("account_name"),
        account_description=cache_data.get("account_description"),
        organization=cache_data.get("organization"),
    )

    frappe.cache().delete_value(f"oauth_state_{state}")
    return _oauth_success_redirect(integration.name)


# =============================================================================
# Integration Management
# =============================================================================


def _save_integration(
    platform: str,
    profile_id: str,
    profile_name: str,
    access_token: str,
    refresh_token: str = None,
    expires_in: int = None,
    page_id: str = None,
    page_access_token: str = None,
    account_type: str = None,
    followers_count: int = 0,
    account_name: str = None,
    organization: str = None,
    account_description: str = None,
    profile_image: str = None,
):
    """Create or update Social Integration"""
    existing = frappe.db.get_value(
        "Social Integration", {"platform": platform, "profile_id": profile_id}, "name"
    )

    if existing:
        integration = frappe.get_doc("Social Integration", existing)
    else:
        integration = frappe.new_doc("Social Integration")
        integration.platform = platform

    integration.profile_id = profile_id
    integration.profile_name = profile_name
    integration.access_token = access_token
    integration.connection_status = "Connected"
    integration.enabled = 1
    integration.last_error = None

    if account_name:
        integration.account_name = account_name
    if account_description:
        integration.account_description = account_description
    if organization:
        integration.organization = organization

    if account_type:
        integration.account_type = account_type
    if followers_count:
        integration.followers_count = followers_count
    if refresh_token:
        integration.refresh_token = refresh_token
    if expires_in:
        integration.token_expiry = add_to_date(now_datetime(), seconds=expires_in)
    if page_id:
        integration.page_id = page_id
    if page_access_token:
        integration.page_access_token = page_access_token
    if profile_image:
        integration.profile_image = profile_image

    integration.save(ignore_permissions=True)

    if profile_image:
        try:
            response = requests.get(profile_image)
            if response.status_code == 200:
                # Guess file extension
                content_type = response.headers.get("content-type", "image/jpeg")
                ext = content_type.split("/")[-1]
                if ext not in ["jpeg", "jpg", "png", "gif", "webp"]:
                    ext = "jpg"

                file_name = f"{platform}_{profile_name}_profile.{ext}"

                file_doc = frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_name": file_name,
                        "attached_to_doctype": "Social Integration",
                        "attached_to_name": integration.name,
                        "attached_to_field": "profile_image",
                        "content": response.content,
                        "is_private": 0,
                        "decode": False,
                    }
                )
                file_doc.insert(ignore_permissions=True)

                # Set the profile_image field to the new file
                integration.profile_image = file_doc.file_url
                integration.save(ignore_permissions=True)

        except Exception as e:
            frappe.log_error(
                f"Failed to fetch profile image for {profile_name}: {str(e)}", "OAuth Profile Image"
            )

    frappe.db.commit()
    return integration


@frappe.whitelist()
def disconnect(integration: str) -> dict:
    doc = frappe.get_doc("Social Integration", integration)
    doc.connection_status = "Not Connected"
    doc.access_token = doc.refresh_token = doc.page_access_token = None
    doc.save(ignore_permissions=True)
    return {"success": True}


@frappe.whitelist()
def test_connection(integration: str) -> dict:
    """Test if integration's connection is valid"""
    doc = frappe.get_doc("Social Integration", integration)
    settings = frappe.get_single("Social Settings")

    try:
        if doc.platform == "Twitter":
            valid = (
                requests.get(
                    "https://api.twitter.com/2/users/me",
                    headers={"Authorization": f"Bearer {doc.get_password('access_token')}"},
                ).status_code
                == 200
            )
        elif doc.platform == "LinkedIn":
            valid = (
                requests.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {doc.get_password('access_token')}"},
                ).status_code
                == 200
            )
        elif doc.platform in ["Facebook", "Instagram"]:
            token = doc.get_password("page_access_token") or doc.get_password("access_token")
            valid = (
                requests.get(
                    f"https://graph.facebook.com/{settings.meta_api_version or 'v21.0'}/me",
                    params={"access_token": token},
                ).status_code
                == 200
            )
        elif doc.platform == "YouTube":
            valid = (
                requests.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "access_token": doc.get_password("access_token"),
                        "part": "snippet",
                        "mine": "true",
                    },
                ).status_code
                == 200
            )
        else:
            valid = False

        doc.connection_status = "Connected" if valid else "Error"
        doc.save(ignore_permissions=True)
        return {"valid": valid}
    except Exception as e:
        doc.connection_status = "Error"
        doc.last_error = str(e)
        doc.save(ignore_permissions=True)
        return {"valid": False, "reason": str(e)}


def _oauth_error_redirect(message: str):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = f"/app/social-integration?error={frappe.utils.quoted(message)}"


def _oauth_success_redirect(integration_name: str):
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = f"/app/social-integration/{integration_name}"
