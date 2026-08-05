from app.services.legacy_test_rag_service import retrieve_similar

r = retrieve_similar(
    "Envoyer une question RH au gestionnaire",
    "Le collaborateur peut envoyer une question RH depuis son espace personnel.",
    k=3,
)
print(f"{len(r)} resultats")
for x in r:
    print(f"- {x['test_id']} score={x['score']} :: {x['title'][:80]}")
    print(f"  pivot.steps count = {len(x['pivot'].get('steps') or [])}")
