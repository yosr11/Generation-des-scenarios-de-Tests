import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Envoie un email contenant le lien de réinitialisation de mot de passe.
    Lit la configuration SMTP depuis les settings.
    """
    # Vérification si le SMTP est configuré
    smtp_host = getattr(settings, "SMTP_HOST", None)
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", None)
    smtp_password = getattr(settings, "SMTP_PASSWORD", None)
    smtp_from = getattr(settings, "SMTP_FROM", smtp_user or "no-reply@soprahr.com")

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning(
            "[EmailService] SMTP non configuré. Lien de réinitialisation pour %s :\n%s",
            to_email,
            reset_url,
        )
        # Retourne False pour indiquer que l'email réel n'a pas pu être envoyé
        return False

    # Création du message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Synaptest — Réinitialisation de votre mot de passe"
    msg["From"] = smtp_from
    msg["To"] = to_email

    text_content = (
        f"Bonjour,\n\n"
        f"Vous avez demandé la réinitialisation de votre mot de passe pour la plateforme Synaptest.\n"
        f"Veuillez cliquer sur le lien ci-dessous pour configurer un nouveau mot de passe :\n"
        f"{reset_url}\n\n"
        f"Ce lien est valable pendant 1 heure.\n\n"
        f"L'équipe Synaptest"
    )

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.6;">
        <div style="max-w: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
          <div style="text-align: center; border-bottom: 2px solid #f43f5e; padding-bottom: 15px; margin-bottom: 20px;">
            <h2 style="color: #0a0f2e; margin: 0;">Synap<span style="color: #f43f5e;">test</span></h2>
            <p style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Plateforme de tests QA</p>
          </div>
          <p>Bonjour,</p>
          <p>Vous avez demandé la réinitialisation de votre mot de passe pour votre compte Synaptest.</p>
          <p>Veuillez cliquer sur le bouton ci-dessous pour configurer un nouveau mot de passe :</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background: linear-gradient(135deg, #ef4444, #f43f5e); color: #ffffff; text-decoration: none; padding: 12px 24px; font-weight: bold; border-radius: 8px; box-shadow: 0 4px 12px rgba(244,63,94,0.3); display: inline-block;">
              Réinitialiser mon mot de passe
            </a>
          </div>
          <p style="font-size: 12px; color: #64748b;">
            Si le bouton ne fonctionne pas, vous pouvez copier et coller le lien suivant dans votre navigateur :<br/>
            <a href="{reset_url}" style="color: #6366f1;">{reset_url}</a>
          </p>
          <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 15px; margin-top: 25px;">
            Ce lien de réinitialisation est valable pendant 1 heure. Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet email en toute sécurité.
          </p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        # STARTTLS uniquement si le serveur le supporte (MailHog en local ne le supporte pas)
        if server.has_extn("STARTTLS"):
            server.starttls()
        # Login uniquement si des identifiants sont fournis (MailHog n'en a pas besoin)
        if smtp_user and smtp_password and smtp_user.lower() != "test":
            server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
        server.quit()
        logger.info("[EmailService] Email envoyé avec succès à %s", to_email)
        return True
    except Exception as exc:
        logger.error(
            "[EmailService] Échec de l'envoi de l'email à %s: %s", to_email, str(exc)
        )
        return False


async def send_account_created_email(
    to_email: str, jira_username: str, display_name: str | None = None
) -> bool:
    """
    Envoie un email de bienvenue lors de la création d'un compte testeur.
    Informe l'utilisateur qu'il peut se connecter avec ses identifiants Jira.
    """
    smtp_host = getattr(settings, "SMTP_HOST", None)
    smtp_port = getattr(settings, "SMTP_PORT", 587)
    smtp_user = getattr(settings, "SMTP_USER", None)
    smtp_password = getattr(settings, "SMTP_PASSWORD", None)
    smtp_from = getattr(settings, "SMTP_FROM", smtp_user or "no-reply@soprahr.com")

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning(
            "[EmailService] SMTP non configuré. Email de bienvenue non envoyé à %s (jira_username=%s)",
            to_email,
            jira_username,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Synaptest — Votre accès a été créé"
    msg["From"] = smtp_from
    msg["To"] = to_email

    text_content = (
        f"Bonjour {display_name or ''},\n\n"
        f"Vous avez accès à Synaptest.\n"
        f"Vous pouvez vous connecter avec vos identifiants de session"
        f"L'équipe Synaptest"
    )

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #1e293b; line-height: 1.6;">
        <div style="max-w: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
          <div style="text-align: center; border-bottom: 2px solid #f43f5e; padding-bottom: 15px; margin-bottom: 20px;">
            <h2 style="color: #0a0f2e; margin: 0;">Synap<span style="color: #f43f5e;">test</span></h2>
            <p style="font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin: 5px 0 0 0;">Plateforme de tests QA</p>
          </div>
          <p>Bonjour {display_name or ''},</p>
          <p><strong>Vous avez accès à Synaptest.</strong></p>
          <p>Vous pouvez vous connecter avec vos identifiants de session:</p>

          <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_BASE_URL.rstrip('/')}/login" style="background: linear-gradient(135deg, #ef4444, #f43f5e); color: #ffffff; text-decoration: none; padding: 12px 24px; font-weight: bold; border-radius: 8px; box-shadow: 0 4px 12px rgba(244,63,94,0.3); display: inline-block;">
              Accéder à Synaptest
            </a>
          </div>
          <p style="font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 15px; margin-top: 25px;">
            Si vous n'êtes pas à l'origine de cette demande, contactez votre administrateur.
          </p>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        # STARTTLS uniquement si le serveur le supporte (MailHog en local ne le supporte pas)
        if server.has_extn("STARTTLS"):
            server.starttls()
        # Login uniquement si des identifiants sont fournis (MailHog n'en a pas besoin)
        if smtp_user and smtp_password and smtp_user.lower() != "test":
            server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, to_email, msg.as_string())
        server.quit()
        logger.info("[EmailService] Email envoyé avec succès à %s", to_email)
        return True
    except Exception as exc:
        logger.error(
            "[EmailService] Échec de l'envoi de l'email à %s: %s", to_email, str(exc)
        )
        return False
