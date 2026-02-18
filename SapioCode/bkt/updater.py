from bkt.model import bkt_update

def update_mastery_bkt(
    current_p: float,
    correct: bool,
    concept_params: dict
) -> float:
    """
    Update mastery using BKT for one student–concept pair.
    """

    return bkt_update(
        p_L=current_p,
        correct=correct,
        p_T=concept_params["p_T"],
        p_S=concept_params["p_S"],
        p_G=concept_params["p_G"]
    )
