"""
Payment Gateway Integration for Khalti and eSewa
Based on official documentation:
- Khalti: https://docs.khalti.com/
- eSewa: https://developer.esewa.com.np/
"""

import hmac
import hashlib
import base64
import uuid
import json
import requests
from django.conf import settings

class KhaltiGateway:
    """
    Khalti Payment Gateway Integration
    Uses Khalti ePayment API v2
    """
    def __init__(self):
        # For sandbox/testing - Using actual credentials from Khalti test merchant dashboard
        self.public_key = getattr(settings, 'KHALTI_PUBLIC_KEY', '6cddd7dc34284795ba952f03c67ee2db')
        self.secret_key = getattr(settings, 'KHALTI_SECRET_KEY', '832cb66ed605485faa6559ba8791ee77')
        self.base_url = "https://a.khalti.com/api/v2"  # Updated sandbox URL

        
    def initiate_payment(self, order_id, amount, return_url, customer_info=None):
        """
        Initiate payment with Khalti
        
        Args:
            order_id: Unique order identifier
            amount: Amount in Rupees (will be converted to Paisa)
            return_url: URL where user will be redirected after payment
            customer_info: Optional dict with name, email, phone
            
        Returns:
            dict with pidx and payment_url on success, error dict on failure
        """
        # Convert amount to Paisa (Rs. 1 = 100 Paisa)
        amount_paisa = int(float(amount) * 100)
        
        # Default customer info if not provided
        if not customer_info:
            customer_info = {
                "name": "FurniQ Customer",
                "email": "customer@furniq.com",
                "phone": "9800000000"
            }
        
        payload = {
            "return_url": return_url,
            "website_url": "http://127.0.0.1:8000/",
            "amount": amount_paisa,
            "purchase_order_id": str(order_id),
            "purchase_order_name": f"FurniQ Order #{order_id}",
            "customer_info": customer_info
        }
        
        headers = {
            'Authorization': f'Key {self.secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/epayment/initiate/",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'error': True,
                'message': str(e),
                'details': response.text if 'response' in locals() else 'Connection error'
            }

    def verify_payment(self, pidx):
        """
        Verify payment status using pidx
        
        Args:
            pidx: Payment identifier returned from initiate_payment
            
        Returns:
            dict with payment details on success
        """
        payload = {"pidx": pidx}
        headers = {
            'Authorization': f'Key {self.secret_key}',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/epayment/lookup/",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'error': True,
                'message': str(e),
                'details': response.text if 'response' in locals() else 'Connection error'
            }


class EsewaGateway:
    """
    eSewa Payment Gateway Integration
    Uses eSewa Epay V2 API
    """
    def __init__(self):
        # Sandbox credentials
        self.merchant_code = 'EPAYTEST'
        self.secret_key = '8gBm/:&EnhH.1/q'  # Sandbox secret
        self.base_url = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
        self.verification_url = "https://rc.esewa.com.np/api/epay/transaction/status/"
        
    def generate_signature(self, total_amount, transaction_uuid, product_code):
        """
        Generate HMAC-SHA256 signature for eSewa
        
        Message format: "total_amount=VALUE,transaction_uuid=VALUE,product_code=VALUE"
        
        Args:
            total_amount: Total amount as string
            transaction_uuid: Unique transaction ID
            product_code: Merchant code (EPAYTEST for sandbox)
            
        Returns:
            Base64 encoded signature
        """
        # Create message string - EXACT format from eSewa docs
        message = f"total_amount={total_amount},transaction_uuid={transaction_uuid},product_code={product_code}"
        
        # Generate HMAC-SHA256
        secret = self.secret_key.encode('utf-8')
        msg = message.encode('utf-8')
        hmac_sha256 = hmac.new(secret, msg, hashlib.sha256)
        
        # Base64 encode
        signature = base64.b64encode(hmac_sha256.digest()).decode('utf-8')
        
        return signature

    def get_payment_data(self, order_id, amount, success_url, failure_url):
        """
        Generate payment form data for eSewa
        
        Args:
            order_id: Unique order identifier
            amount: Amount in Rupees
            success_url: URL for successful payment
            failure_url: URL for failed payment
            
        Returns:
            dict with form fields for eSewa payment
        """
        # Generate unique transaction UUID
        transaction_uuid = f"{order_id}-{uuid.uuid4().hex[:8]}"
        
        # Convert amount to string (eSewa requires string)
        total_amount = str(int(float(amount)))
        
        # Generate signature
        signature = self.generate_signature(
            total_amount,
            transaction_uuid,
            self.merchant_code
        )
        
        return {
            'amount': total_amount,
            'tax_amount': '0',
            'total_amount': total_amount,
            'transaction_uuid': transaction_uuid,
            'product_code': self.merchant_code,
            'product_service_charge': '0',
            'product_delivery_charge': '0',
            'success_url': success_url,
            'failure_url': failure_url,
            'signed_field_names': 'total_amount,transaction_uuid,product_code',
            'signature': signature,
            'action_url': self.base_url
        }

    def verify_payment(self, product_code, total_amount, transaction_uuid):
        """
        Verify payment with eSewa
        
        Args:
            product_code: Merchant code
            total_amount: Total amount
            transaction_uuid: Transaction UUID
            
        Returns:
            dict with verification result
        """
        params = {
            'product_code': product_code,
            'total_amount': total_amount,
            'transaction_uuid': transaction_uuid
        }
        
        try:
            response = requests.get(
                self.verification_url,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Check if status is COMPLETE
            if data.get('status') == 'COMPLETE':
                return {
                    'success': True,
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'message': 'Payment not completed',
                    'data': data
                }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': True,
                'message': str(e),
                'details': response.text if 'response' in locals() else 'Connection error'
            }

