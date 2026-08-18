import os
import logging
import resend
from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

logger = logging.getLogger(__name__)

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    # Weka Resend API Key kutoka Render Environment Variable
    resend.api_key = os.environ.get('RESEND_API_KEY')

    # Link ya Reset Password kwenye Frontend ya Vercel
    frontend_url = "https://selguudi-frontend-git-main-anoldius1.vercel.app/reset-password"
    reset_url = f"{frontend_url}?token={reset_password_token.key}"

    # Email Body (HTML & Plain Text)
    recipient_email = reset_password_token.user.email
    username = reset_password_token.user.username

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 600px; margin: auto;">
        <h2 style="color: #10b981;">Selguudi POS</h2>
        <p>Habari <strong>{username}</strong>,</p>
        <p>Umetuma maombi ya kubadilisha nenosiri kwenye mfumo wa Selguudi POS.</p>
        <p>Bofya kitufe hapa chini ili kubadilisha nenosiri yako:</p>
        <p style="margin: 25px 0;">
            <a href="{reset_url}" style="background-color: #10b981; color: #fff; padding: 12px 20px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                Badilisha Nenosiri
            </a>
        </p>
        <p>Au tumia Token hii: <strong>{reset_password_token.key}</strong></p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
        <p style="font-size: 12px; color: #777;">Ikiwa hukutuma maombi haya, tafadhali puuzia barua pepe hii.</p>
    </div>
    """

    try:
        # Tuma Email kupitia Resend HTTP API
        response = resend.Emails.send({
            "from": "Selguudi POS <onboarding@resend.dev>",
            "to": [recipient_email],
            "subject": "Maombi ya Kubadilisha Nenosiri - Selguudi POS",
            "html": html_content,
        })
        logger.info(f"Resend Email sent to {recipient_email}. ID: {response}")
    except Exception as e:
        logger.error(f"Failed to send email via Resend to {recipient_email}: {str(e)}")
        raise e