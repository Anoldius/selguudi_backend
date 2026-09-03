import requests
from django.conf import settings

# Base URL za PesaPal V3
PESAPAL_BASE_URL = getattr(settings, 'PESAPAL_BASE_URL', 'https://pay.pesapal.com/v3')
PESAPAL_KEY = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
PESAPAL_SECRET = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')

def get_pesapal_token():
    """Vuta Request Token kutoka PesaPal V3 API"""
    urls_to_try = [
        "https://pay.pesapal.com/v3/api/Auth/RequestToken",
        "https://cyb3rpay.pesapal.com/pesapalv3/api/Auth/RequestToken"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "consumer_key": PESAPAL_KEY.strip(),
        "consumer_secret": PESAPAL_SECRET.strip()
    }

    for url in urls_to_try:
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                token = data.get('token')
                if token:
                    return token
            else:
                print(f"Error from {url}: {response.text}")
        except Exception as e:
            print(f"Exception from {url}: {e}")

    return None


def register_pesapal_ipn(token, ipn_url=None):
    """Sajili IPN Webhook URL PesaPal (Inatumia domain mpya)"""
    if not ipn_url:
        ipn_url = "https://selguudi-backend.onrender.com/api/accounts/billing/pesapal-ipn/"

    base_url = "https://pay.pesapal.com/v3"
    url = f"{base_url}/api/URLSetup/RegisterIPN"
    
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
        else:
            print(f"IPN Registration Error: {response.text}")
    except Exception as e:
        print("PesaPal IPN Register Exception:", e)
    return None


def submit_pesapal_order(token, order_payload):
    """Tuma ombi la kutengeneza Link ya Malipo kuenda PesaPal V3"""
    base_urls = ["https://pay.pesapal.com/v3", "https://cyb3rpay.pesapal.com/pesapalv3"]
    
    # Hakikisha callback_url inatumia domain mpya ya selguudi.co.tz
    if 'callback_url' in order_payload:
        order_payload['callback_url'] = "https://selguudi.co.tz/billing/success"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    for base_url in base_urls:
        url = f"{base_url}/api/Transactions/SubmitOrderRequest"
        try:
            response = requests.post(url, json=order_payload, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Submit Order Error from {url}: {response.text}")
        except Exception as e:
            print(f"Submit Order Exception from {url}: {e}")

    return None