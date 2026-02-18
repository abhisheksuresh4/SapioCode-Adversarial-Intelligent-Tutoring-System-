from bkt.updater import update_mastery_bkt
from bkt.affect_fusion import modulate_bkt_params
from bkt.explainability import explain_bkt_update


def process_submission_bkt(
    neo4j_session,
    sid: str,
    sub_id: str,
    correct: bool,
    cognitive_state: dict | None = None
):
    """
    Orchestrates BKT updates for one submission.
    """

   
    if cognitive_state is None:
        cognitive_state = {
            "engagement": 0.7,
            "frustration": 0.1,
            "confusion": 0.2,
            "boredom": 0.0
        }

   
    results = neo4j_session.run(
        """
        MATCH (s:Student {sid: $sid})-[m:MASTERY]->(c:Concept)
        MATCH (s)-[:MADE]->(sub:Submission {sub_id: $sub_id})
        MATCH (sub)-[:OF_PROBLEM]->(:Problem)-[:TESTS]->(c)
        RETURN
          c.name AS concept,
          m.p AS current_mastery,
          c.bkt_p_T AS p_T,
          c.bkt_p_S AS p_S,
          c.bkt_p_G AS p_G
        """,
        sid=sid,
        sub_id=sub_id
    )
    for record in results:
        old_p = record["current_mastery"]

        base_params = {
            "p_T": record["p_T"],
            "p_S": record["p_S"],
            "p_G": record["p_G"]
        }

        adapted_params = modulate_bkt_params(
            base_params=base_params,
            cognitive_state=cognitive_state
        )

        new_p = update_mastery_bkt(
            current_p=old_p,
            correct=correct,
            concept_params=adapted_params
        )

      
        explanation = explain_bkt_update(
            cognitive_state=cognitive_state,
            base_params=base_params,
            adapted_params=adapted_params,
            old_mastery=old_p,
            new_mastery=new_p
        )

        print(f"[BKT] Concept: {record['concept']}")
        print("EXPLANATION:", explanation["summary"])

 
        neo4j_session.run(
            """
            MATCH (s:Student {sid: $sid})-[m:MASTERY]->(c:Concept {name: $concept})
            SET m.p = $new_p
            """,
            sid=sid,
            concept=record["concept"],
            new_p=new_p
        )

    