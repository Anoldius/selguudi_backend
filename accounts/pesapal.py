import requests
from django.conf import settings

# Base URLs za PesaPal (Inajumuisha zote ili isome ipi inaruhusiwa na keys zako)
PESAPAL_BASE_URL = getattr(settings, 'PESAPAL_BASE_URL', 'https://pay.pesapal.com/v3')
PESAPAL_KEY = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
PESAPAL_SECRET = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')


def get_pesapal_token():
    """Vuta Request Token kutoka PesaPal (Inajaribu URLs zote)"""
    urls_to_try = [
        f"{PESAPAL_BASE_URL}/api/Auth/RequestToken",
        "https://pay.pesapal.com/v3/api/Auth/RequestToken",
        "https://cyb3rpay.pesapal.com/pesapalv3/api/Auth/RequestToken"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "consumer_key": str(PESAPAL_KEY).strip(),
        "consumer_secret": str(PESAPAL_SECRET).strip()
    }

    for url in urls_to_try:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                token = response.json().get('token')
                if token:
                    return token
            else:
                print(f"Token Error from {url} [{response.status_code}]: {response.text}")
        except Exception as e:
            print(f"Token Exception from {url}: {e}")

    return None


def register_pesapal_ipn(token, ipn_url=None):
    """Sajili IPN Webhook URL PesaPal"""
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
        print(f"IPN Reg Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print("IPN Register Exception:", e)
    return None


def submit_pesapal_order(token, order_payload):
    """Tuma ombi la kutengeneza Link ya Malipo (Inajaribu zote)"""
    base_urls = [PESAPAL_BASE_URL, "https://pay.pesapal.com/v3", "https://cyb3rpay.pesapal.com/pesapalv3"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    for base in base_urls:
        url = f"{base}/api/Transactions/SubmitOrderRequest"
        try:
            response = requests.post(url, json=order_payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Submit Order Error from {url} [{response.status_code}]: {response.text}")
        except Exception as e:
            print(f"Submit Order Exception from {url}: {e}")

    return None


def get_pesapal_transaction_status(token, order_tracking_id):
    """Kagua Hali ya Muamala"""
    base_urls = [PESAPAL_BASE_URL, "https://pay.pesapal.com/v3", "https://cyb3rpay.pesapal.com/pesapalv3"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    for base in base_urls:
        url = f"{base}/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Get Status Exception from {url}: {e}")

    return None