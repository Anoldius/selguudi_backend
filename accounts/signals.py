import logging
from django.dispatch import receiver
from django.core.mail import send_mail
from django_rest_passwordreset.signals import reset_password_token_created

logger = logging.getLogger(__name__)

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    frontend_url = "https://selguudi-frontend-git-main-anoldius1.vercel.app/reset-password"
    reset_url = f"{frontend_url}?token={reset_password_token.key}"

    email_subject = "Maombi ya Kubadilisha Nenosiri - Selguudi POS"
    
    email_message = f"""
Habari {reset_password_token.user.username},

Umetuma maombi ya kubadilisha nenosiri kwenye mfumo wa Selguudi POS.

Bofya kiungo hiki ili kubadilisha nenosiri lako:
{reset_url}

Token yako ya kubadilisha nenosiri ni: {reset_password_token.key}

Ikiwa hukutuma maombi haya, tafadhali puuzia barua pepe hii.

Wako,
Selguudi POS Team.
"""

    try:
        send_mail(
            subject=email_subject,
            message=email_message,
            from_email=None,  # Inatumia DEFAULT_FROM_EMAIL ya settings.py
            recipient_list=[reset_password_token.user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email successfully sent to {reset_password_token.user.email}")
    except Exception as e:
        logger.error(f"Failed to send email to {reset_password_token.user.email}: {str(e)}")
        # Raise Exception ili API irudishe kosa halisi badala ya kuficha
        raise e