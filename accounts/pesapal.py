import requests
from django.conf import settings

PESAPAL_BASE_URL = getattr(settings, 'PESAPAL_BASE_URL', 'https://cyb3rpay.pesapal.com/pesapalv3')
PESAPAL_KEY = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
PESAPAL_SECRET = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')

def get_pesapal_token():
    """1. Vuta Request Token kutoka PesaPal V3 API"""
    url = f"{PESAPAL_BASE_URL}/api/Auth/RequestToken"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "consumer_key": PESAPAL_KEY,
        "consumer_secret": PESAPAL_SECRET
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            print("PesaPal Token Error Response:", response.text)
    except Exception as e:
        print("PesaPal Token Request Exception:", e)
    return None


def register_pesapal_ipn(token, ipn_url):
    """2. Sajili IPN Webhook URL PesaPal kupata notification_id"""
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
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('ipn_id')
    except Exception as e:
        print("PesaPal IPN Register Exception:", e)
    return None


def submit_pesapal_order(token, order_payload):
    """3. Tuma ombi la kutengeneza Link ya Malipo (Payment Page)"""
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
        else:
            print("PesaPal Submit Order Error Response:", response.text)
    except Exception as e:
        print("PesaPal Submit Order Exception:", e)
    return None