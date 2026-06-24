"""Merge des entrées d'analyse complétées manuellement dans agent1 prediction.json."""
import json
from pathlib import Path

PRED_FILE = Path("eval/agent1 prediction.json")

UPDATES = [
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": None,
        "story": {
            "id": "NUXEPM-2340",
            "summary": "4YOU 5415 - NB JRS DEBUT 2026 Encore Associé à 2025 au RRH",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_COMMUN"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2340",
            "story_title": "4YOU 5415 - NB JRS DEBUT 2026 Encore Associé à 2025 au RRH",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-637", "summary": "Espace RRH de proximité"},
        "story": {
            "id": "NUXEPM-2319",
            "summary": "RH de proximité - Tester unitairement les développements sur l'environnement QA80 de perf",
            "description_clean": "Tester les fonctionnalités du RRH sur l'environnement QA80 dédiée au perf et analyser les temps de réponses lorsqu'il y a de la volumétrie.",
            "acceptance_criteria_clean": "",
            "labels": ["STANDBY_2024", "STREAM_APPLICATIF"],
            "priority": "P2-Medium",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2319",
            "story_title": "RH de proximité - Tester unitairement les développements sur l'environnement QA80 de perf",
            "story_type": "technical",
            "actors": [], "actions": [], "business_rules": [],
            "technical_scope": ["environnement QA80", "perf"],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [],
            "analysis_reason": [
                "La story concerne des tests unitaires sur un environnement spécifique.",
                "Pas de changement fonctionnel décrit."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": None,
        "story": {
            "id": "NUXEPM-2313",
            "summary": "Traitement des retours de bench 9.0 (2026)",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_CORE"],
            "priority": "P2-Medium",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2313",
            "story_title": "Traitement des retours de bench 9.0 (2026)",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-637", "summary": "Espace RRH de proximité"},
        "story": {
            "id": "NUXEPM-2305",
            "summary": "ST18_RH de proximité : Fonction de recherche sur la nouvelle vue \"Par collaborateur \" de l'inbox CSP",
            "description_clean": "[En tant que] RRH de proximité\n[Je souhaite] pouvoir rechercher un collaborateur dans une vue Par collaborateur de mon inbox CSP\n[afin] d’accéder rapidement à l'information du collaborateur.\nCette capacité de recherche dans la Vue par collaborateur sera aussi affichée pour tout type de gestionnaire (Gestionnaire RH, Gestionnaire Paie, etc)\n[+ infos]\najouter une Fonction de recherche d’un collaborateur en particulier parmi ceux ayant des demandes à traiter dans la vue Par collaborateur\nreprésentation par un champ recherche avec loupe\nCette évolution avait été demandée dans le https://hra-jira.ptx.fr.sopra/browse/NUXEPM-1871 du RRH de proximité Lot2 (voir Illustration)",
            "acceptance_criteria_clean": "",
            "labels": ["PP2026", "STREAM_APPLICATIF"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2305",
            "story_title": "ST18_RH de proximité : Fonction de recherche sur la nouvelle vue 'Par collaborateur ' de l'inbox CSP",
            "story_type": "functional",
            "actors": ["RRH de proximité", "Gestionnaire RH", "Gestionnaire Paie"],
            "actions": [
                "rechercher un collaborateur dans la vue Par collaborateur",
                "accéder rapidement à l'information du collaborateur"
            ],
            "business_rules": [],
            "technical_scope": [],
            "testable_points": [
                "Verifier que le champ de recherche avec loupe est affiché au-dessus de la liste des collaborateurs",
                "Verifier que la recherche d'un collaborateur en particulier est possible parmi ceux ayant des demandes à traiter dans la vue Par collaborateur",
                "Verifier que les résultats de la recherche sont affichés correctement pour les collaborateurs",
                "Verifier que la fonctionnalité de recherche est également disponible pour les autres types de gestionnaires (Gestionnaire RH, Gestionnaire Paie, etc.)"
            ],
            "user_flows": [
                "Le RRH de proximité se connecte à son inbox CSP",
                "Il sélectionne la vue Par collaborateur",
                "Il utilise le champ de recherche avec loupe pour rechercher un collaborateur",
                "Il accède rapidement à l'information du collaborateur"
            ],
            "acceptance_criteria_explicit": [
                "La fonctionnalité de recherche est disponible pour les RRH de proximité",
                "La fonctionnalité de recherche est également disponible pour les autres types de gestionnaires",
                "Les résultats de la recherche sont classés correctement"
            ],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Quelles sont les critères de recherche possibles pour les collaborateurs ?",
                "Comment les résultats de la recherche sont-ils classés et affichés ?"
            ],
            "analysis_reason": [
                "La story décrit une fonctionnalité de recherche pour les RRH de proximité et les autres gestionnaires",
                "La story mentionne des critères d'acceptation explicites pour la fonctionnalité"
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "PPBACKLOG-2293", "summary": "PUBLIC - 2024 - HRA4YOU Public "},
        "story": {
            "id": "NUXEPM-2298",
            "summary": "PPBACKLOG-663 - 4YOU - nouvelle démarche - demander une position administrative - Assistance 5414 auprès des équipes Public",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["4YOU_9.1"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2298",
            "story_title": "PPBACKLOG-663 - 4YOU - nouvelle démarche - demander une position administrative - Assistance 5414 auprès des équipes Public",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "PPBACKLOG-2293", "summary": "PUBLIC - 2024 - HRA4YOU Public "},
        "story": {
            "id": "NUXEPM-2297",
            "summary": "PPBACKLOG-664 - 4YOU - nouvelle démarche - demander un changement de modalités de service - Assistance 5414 auprès des équipes Public",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": [],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2297",
            "story_title": "PPBACKLOG-664 - 4YOU - nouvelle démarche - demander un changement de modalités de service - Assistance 5414 auprès des équipes Public",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "PPBACKLOG-7706", "summary": "Extension Démarches Modulaires"},
        "story": {
            "id": "NUXEPM-2296",
            "summary": "PPBACKLOG-3139 - Intégration du dispositif CET : nouvelles démarches (Support et Assistance 5414)",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["4YOU_9.1"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2296",
            "story_title": "PPBACKLOG-3139 - Intégration du dispositif CET : nouvelles démarches (Support et Assistance 5414)",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-1840", "summary": "K-NEWS - Gestion des news dans 4YOU (lot2) - Annonces - Actualités "},
        "story": {
            "id": "NUXEPM-2293",
            "summary": "News - MACRO ENVELOP SUR CAPACITE RESTANTE",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["Candidat_V10", "Chiffrage-9.0.X-Done", "Grooming-1510", "K-DATA", "STREAM_CORE", "STREAM_HUB"],
            "priority": "P1-High",
            "status": "Ready"
        },
        "analysis": {
            "story_id": "NUXEPM-2293",
            "story_title": "News - MACRO ENVELOP SUR CAPACITE RESTANTE",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-1840", "summary": "K-NEWS - Gestion des news dans 4YOU (lot2) - Annonces - Actualités "},
        "story": {
            "id": "NUXEPM-2270",
            "summary": "News - Enveloppe Fixing",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["Candidat_V10", "Chiffrage-9.0.X-Done", "Grooming-1510", "K-DATA", "STREAM_CORE", "STREAM_HUB"],
            "priority": "P1-High",
            "status": "Ready"
        },
        "analysis": {
            "story_id": "NUXEPM-2270",
            "story_title": "News - Enveloppe Fixing",
            "story_type": "invalid_or_too_weak",
            "actors": [], "actions": [], "business_rules": [], "technical_scope": [],
            "testable_points": [], "user_flows": [],
            "acceptance_criteria_explicit": [], "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-637", "summary": "Espace RRH de proximité"},
        "story": {
            "id": "NUXEPM-2233",
            "summary": "ST17_RH de proximité - Prise en compte de l'acteur \"Superviseur\" dans SYD et Sidebarre",
            "description_clean": "Prise en compte de l'acteur \"Superviseur\" pour les combinaisons d'acteurs suivantes :\nRRH de proximité \"Superviseur\" (Global et local (établissement)\nRRH de proximité \"Superviseur\" (Global et local (établissement)+ Gestionnaire Paie et/ou Gestionnaire RH\ndans la page d'accueil (SYD)  et la sidebarre qui apparaît à gauche de l'inbox CSP, de l'indicateur Contrôles de paie, des pages Mes collaborateurs et Processus RH et de la page Pilotage CSP d'un \"Superviseur\"",
            "acceptance_criteria_clean": "",
            "labels": ["PP2025", "QA", "STREAM_APPLICATIF"],
            "priority": "P1-High",
            "status": "Done-Done"
        },
        "analysis": {
            "story_id": "NUXEPM-2233",
            "story_title": "ST17_RH de proximité - Prise en compte de l'acteur \"Superviseur\" dans SYD et Sidebarre",
            "story_type": "functional",
            "actors": ["RRH de proximité", "Superviseur", "Gestionnaire Paie", "Gestionnaire RH"],
            "actions": [
                "afficher les SYD correspondants aux combinaisons d'acteurs",
                "afficher et gérer la sidebarre sur toutes les pages la présentant",
                "sélectionner l'indicateur Contrôles de paie",
                "accéder à la page Pilotage CSP",
                "accéder à la page Mes collaborateurs",
                "accéder à la page Processus RH"
            ],
            "business_rules": [
                "prise en compte de l'acteur 'Superviseur' pour les combinaisons d'acteurs suivantes : RRH de proximité 'Superviseur' (Global et local (établissement))",
                "prise en compte de l'acteur 'Superviseur' pour les combinaisons d'acteurs suivantes : RRH de proximité 'Superviseur' (Global et local (établissement) + Gestionnaire Paie et/ou Gestionnaire RH"
            ],
            "technical_scope": [],
            "testable_points": [
                "Vérifier que l'acteur 'Superviseur' est pris en compte dans la page d'accueil (SYD)",
                "Vérifier que l'acteur 'Superviseur' est pris en compte dans la sidebarre qui apparaît à gauche de l'inbox CSP",
                "Vérifier que l'acteur 'Superviseur' est pris en compte dans l'indicateur Contrôles de paie",
                "Vérifier que l'acteur 'Superviseur' est pris en compte dans les pages Mes collaborateurs et Processus RH",
                "Vérifier que l'acteur 'Superviseur' est pris en compte dans la page Pilotage CSP"
            ],
            "user_flows": [
                "Accéder à la page d'accueil (SYD) en tant que RRH de proximité 'Superviseur'",
                "Accéder à la sidebarre en tant que RRH de proximité 'Superviseur'",
                "Sélectionner l'indicateur Contrôles de paie en tant que RRH de proximité 'Superviseur'",
                "Accéder à la page Mes collaborateurs en tant que RRH de proximité 'Superviseur'",
                "Accéder à la page Processus RH en tant que RRH de proximité 'Superviseur'",
                "Accéder à la page Pilotage CSP en tant que RRH de proximité 'Superviseur'"
            ],
            "acceptance_criteria_explicit": [
                "Prise en compte de l'acteur 'Superviseur' pour les combinaisons d'acteurs suivantes : RRH de proximité 'Superviseur' (Global et local (établissement))",
                "Prise en compte de l'acteur 'Superviseur' pour les combinaisons d'acteurs suivantes : RRH de proximité 'Superviseur' (Global et local (établissement) + Gestionnaire Paie et/ou Gestionnaire RH"
            ],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Quelles sont les combinaisons d'acteurs prises en compte pour l'acteur 'Superviseur' ?",
                "Quels sont les écrans et les fonctionnalités affectés par la prise en compte de l'acteur 'Superviseur' ?"
            ],
            "analysis_reason": [
                "La story décrit une fonctionnalité qui affecte les utilisateurs finaux.",
                "La story mentionne des acteurs et des actions spécifiques.",
                "La story nécessite des vérifications QA concrètes et observables."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {
            "key": "NUXEPM-1840",
            "summary": "K-NEWS - Gestion des news dans 4YOU (lot2) - Annonces - Actualités "
        },
        "story": {
            "id": "NUXEPM-2416",
            "summary": "News - Filtre sur les métadonnées dans la Recherche",
            "description_clean": "L'ajout du composant \"rich-editor\" a provoqué un effet de bord au niveau de la recherche. On peut désormais avoir des faux positifs avec les métadonnées suivantes : type, doc, heading, paragraph, text, table, content, attrs, align, null, indent, level, table, tablerow, tableheader, colspan, rowspan, colwidth, background, tablecell, marks, strong, em, u, textcolor, color, textbackgroundcolor, backgroundColor, s, sub, sup, orderedlist, order, listitem, bullet_list.",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_APPLICATIF"],
            "priority": "P1-High",
            "status": "Done"
        },
        "analysis": {
            "story_id": "NUXEPM-2416",
            "story_title": "News - Filtre sur les métadonnées dans la Recherche",
            "story_type": "functional",
            "actors": ["AUTEUR des News"],
            "actions": ["Filtrer les métadonnées dans la Recherche"],
            "business_rules": ["Empêcher les faux positifs avec les métadonnées"],
            "technical_scope": [],
            "testable_points": [
                "Verifier que les métadonnées suivantes ne provoquent plus de faux positifs : type, doc, heading, paragraph, text, table, content, attrs, align, null, indent, level, table, tablerow, tableheader, colspan, rowspan, colwidth, background, tablecell, marks, strong, em, u, textcolor, color, textbackgroundcolor, backgroundColor, s, sub, sup, orderedlist, order, listitem, bullet_list",
                "Verifier que la recherche fonctionne correctement après l'ajout du composant 'rich-editor'"
            ],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Quelles sont les métadonnées exactes qui provoquent des faux positifs ?",
                "Comment le filtre sur les métadonnées est-il configuré ?"
            ],
            "analysis_reason": [
                "La story décrit une problématique fonctionnelle avec la recherche après l'ajout d'un composant.",
                "La story mentionne des métadonnées spécifiques qui provoquent des faux positifs."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": None,
        "story": {
            "id": "NUXEPM-2415",
            "summary": "IA 4 SOFTWARE ENGINEERING - Etudes des performances avec l'IA",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["4YOU_9.1", "STREAM_CORE"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2415",
            "story_title": "IA 4 SOFTWARE ENGINEERING - Etudes des performances avec l'IA",
            "story_type": "invalid_or_too_weak",
            "actors": [],
            "actions": [],
            "business_rules": [],
            "technical_scope": [],
            "testable_points": [],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "PPBACKLOG-477", "summary": "Plateforme 4YOU - Dette technique"},
        "story": {
            "id": "NUXEPM-2398",
            "summary": "Bench - Création automatique de demandes de congés",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_CORE"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2398",
            "story_title": "Bench - Création automatique de demandes de congés",
            "story_type": "invalid_or_too_weak",
            "actors": [],
            "actions": [],
            "business_rules": [],
            "technical_scope": [],
            "testable_points": [],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "PPBACKLOG-477", "summary": "Plateforme 4YOU - Dette technique"},
        "story": {
            "id": "NUXEPM-2397",
            "summary": "4YOU ASSIST - Résolution des libraires externes",
            "description_clean": "Comment déclarer l'accès depuis la V9 à des librairies externes qui pourraient être utiles à \"Mon assisant 4YOU\" (fonctionnalité qui était possible en V8), comme par exemple l'ajout de :\nLibrairies techniques éventuelles\nLibrairies graphiques front (ex pour afficher des plans et trajets : \\[Leaflet et WMTS | Géoservices|https://eur01.safelinks.protection.outlook.com/?url=https%3A%2F%2Fgeoservices.ign.fr%2Fdocumentation%2Fservices%2Futilisation-web%2Faffichage-wmts%2Fleaflet-et-wmts&data=05%7C02%7Claurent.bossart%40soprahr.com%7C8b84c7e2b3a4426bffde08de84027d52%7C8b87af7d86474dc78df45f69a2011bb5%7C0%7C0%7C639093343400159057%7CUnknown%7CTWFpbGZsb3d8eyJFbXB0eU1hcGkiOnRydWUsIlYiOiIwLjAuMDAwMCIsIlAiOiJXaW4zMiIsIkFOIjoiTWFpbCIsIldUIjoyfQ%3D%3D%7C0%7C%7C%7C&sdata=UcvhIPb9xelFM9I5Gv%2BKFxdwqjN6Mmpf5BAIiLW0Kro%3D&reserved=0]\\)",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_CORE"],
            "priority": "P1-High",
            "status": "To Be Detailed"
        },
        "analysis": {
            "story_id": "NUXEPM-2397",
            "story_title": "4YOU ASSIST - Résolution des libraires externes",
            "story_type": "technical",
            "actors": [],
            "actions": [],
            "business_rules": [],
            "technical_scope": ["librairies externes", "Leaflet", "WMTS", "Géoservices"],
            "testable_points": [],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [],
            "analysis_reason": [
                "La story concerne la résolution des librairies externes pour 4YOU ASSIST, sans modification de comportement visible pour l'utilisateur."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": None,
        "story": {
            "id": "NUXEPM-2358",
            "summary": "Modularisation du START YOUR DAY COLLAB/MANAGER Pour Pléiades (Pré-recquis pour widget pointage)",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["STREAM_APPLICATIF"],
            "priority": "P1-High",
            "status": "Done-Done"
        },
        "analysis": {
            "story_id": "NUXEPM-2358",
            "story_title": "Modularisation du START YOUR DAY COLLAB/MANAGER Pour Pléiades (Pré-recquis pour widget pointage)",
            "story_type": "invalid_or_too_weak",
            "actors": [],
            "actions": [],
            "business_rules": [],
            "technical_scope": [],
            "testable_points": [],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
    {
        "model_alias": "llama4",
        "provider": "groq",
        "model_name": "meta-llama/llama-4-scout-17b-16e-instruct",
        "epic": {"key": "NUXEPM-637", "summary": "Espace RRH de proximité"},
        "story": {
            "id": "NUXEPM-2341",
            "summary": "RH PROXIMITE FIXING NON RATTACHABLE AU NUXEPM EXISTANT",
            "description_clean": "",
            "acceptance_criteria_clean": "",
            "labels": ["PP2025", "QA", "STREAM_APPLICATIF"],
            "priority": "P1-High",
            "status": "Done-Done"
        },
        "analysis": {
            "story_id": "NUXEPM-2341",
            "story_title": "RH PROXIMITE FIXING NON RATTACHABLE AU NUXEPM EXISTANT",
            "story_type": "invalid_or_too_weak",
            "actors": [],
            "actions": [],
            "business_rules": [],
            "technical_scope": [],
            "testable_points": [],
            "user_flows": [],
            "acceptance_criteria_explicit": [],
            "acceptance_criteria_inferred": [],
            "clarification_questions": [
                "Pouvez-vous compléter la description de la story ?",
                "Pouvez-vous ajouter des critères d’acceptation clairs ?"
            ],
            "analysis_reason": [
                "La story ne contient pas de description exploitable.",
                "Aucun comportement testable ne peut être identifié.",
                "Action requise : contacter le Product Owner pour enrichir la story."
            ],
            "resolved_from_references": []
        }
    },
]


def main() -> None:
    data = json.loads(PRED_FILE.read_text(encoding="utf-8-sig"))
    results = data["results"]

    by_id = {r["story"]["id"]: i for i, r in enumerate(results)}
    updated, missing = [], []

    for upd in UPDATES:
        sid = upd["story"]["id"]
        if sid in by_id:
            results[by_id[sid]] = upd
            updated.append(sid)
        else:
            missing.append(sid)

    PRED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Updated: {len(updated)} -> {updated}")
    if missing:
        print(f"MISSING (not found in file): {missing}")
    print(f"Total results in file: {len(results)}")


if __name__ == "__main__":
    main()
