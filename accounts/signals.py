from django.dispatch import receiver
from django.core.mail import send_mail
from django_rest_passwordreset.signals import reset_password_token_created

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    # Link ya Frontend Vercel yenye Token
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

    send_mail(
        subject=email_subject,
        message=email_message,
        from_email='Selguudi POS <noreply@selguudipos.com>',
        recipient_list=[reset_password_token.user.email],
        fail_silently=False,
    )