from django.dispatch import receiver
from django.core.mail import send_mail
from django_rest_passwordreset.signals import reset_password_token_created

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    token_key = reset_password_token.key
    user_email = reset_password_token.user.email

    # Print kubwa ya wazi kwenye terminal
    print("\n" + "="*60)
    print("🔑 PASSWORD RESET TOKEN SUCCESSFUL!")
    print(f"📧 USER EMAIL : {user_email}")
    print(f"🎟️ TOKEN KEY  : {token_key}")
    print("="*60 + "\n")

    # Tuma pia console email
    try:
        send_mail(
            subject=f"Password Reset for {reset_password_token.user.username}",
            message=f"Token yako ya ku-reset password ni: {token_key}",
            from_email="Selguudi POS <noreply@selguudipos.com>",
            recipient_list=[user_email],
            fail_silently=False,
        )
    except Exception as e:
        print("Mail error:", e)