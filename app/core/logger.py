#Configure le logging (affichage propre des logs).
#Utile pour le debug + production.

import logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("PFE-AGENT-TEST")