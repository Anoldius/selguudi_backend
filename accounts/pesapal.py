import requests
from django.conf import settings

# Base URL na Credentials kutoka Settings (Strictly Live)
PESAPAL_BASE_URL = "https://pay.pesapal.com/v3"
PESAPAL_KEY = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
PESAPAL_SECRET = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')


def get_pesapal_token():
    """Vuta Request Token kutoka PesaPal Live V3 API"""
    url = f"{PESAPAL_BASE_URL}/api/Auth/RequestToken"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "consumer_key": str(PESAPAL_KEY).strip(),
        "consumer_secret": str(PESAPAL_SECRET).strip()
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                return token
        print(f"PesaPal Live Token Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"PesaPal Token Exception: {e}")

    return None


def register_pesapal_ipn(token, ipn_url=None):
    """Sajili IPN Webhook URL PesaPal (Live Domain)"""
    if not ipn_url:
        ipn_url = "https://api.selguudi.co.tz/api/accounts/billing/pesapal-ipn/"

    url = f"{PESAPAL_BASE_URL}/api/URLSetup/RegisterIPN"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "url": ipn_url,
        "ipn_notification_type": "GET"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get('ipn_id')
        print(f"PesaPal IPN Reg Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print("PesaPal IPN Register Exception:", e)
    return None


def submit_pesapal_order(token, order_payload):
    """Tuma ombi la kutengeneza Link ya Malipo Live V3"""
    url = f"{PESAPAL_BASE_URL}/api/Transactions/SubmitOrderRequest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(url, json=order_payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        print(f"Submit Order Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"Submit Order Exception: {e}")

    return None


def get_pesapal_transaction_status(token, order_tracking_id):
    """Kagua Hali ya Muamala (Transaction Status) Live V3 API"""
    url = f"{PESAPAL_BASE_URL}/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json()
        print(f"Get Transaction Status Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"Get Transaction Status Exception: {e}")

    return None