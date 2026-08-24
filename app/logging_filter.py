import logging


class NoiseFilter(logging.Filter):
    """Masque les logs des requêtes de scan automatique (404, sondes JNDI/Struts/etc.)."""

    BLOCKED_SNIPPETS = (
        "%3Aundefined",
        "jndi:",
        "struts2-showcase",
        "broker/xml",
        "webtools/control",
        "JSPWiki",
        "cgi-bin",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        # Masque les 404 génériques (routes inexistantes = bruit de scan)
        if '" 404' in message:
            return False

        # Masque les 401 sur /auth/me (normal tant qu'on n'est pas connecté)
        if "/auth/me" in message and '" 401' in message:
            return False

        return True