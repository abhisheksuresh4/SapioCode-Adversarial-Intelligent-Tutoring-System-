def explain_bkt_update(
    cognitive_state: dict,
    base_params: dict,
    adapted_params: dict,
    old_mastery: float,
    new_mastery: float
) -> dict:
    """
    Generate human-readable explanation for mastery update.
    """

    explanations = []

    # Affect-based reasoning
    if cognitive_state.get("frustration", 0) > 0.5:
        explanations.append(
            "Learning rate was reduced due to high frustration."
        )

    if cognitive_state.get("engagement", 0) > 0.5:
        explanations.append(
            "Learning rate was increased due to strong engagement."
        )

    if cognitive_state.get("confusion", 0) > 0.4:
        explanations.append(
            "Error probability increased due to observed confusion."
        )

    if cognitive_state.get("boredom", 0) > 0.5:
        explanations.append(
            "Guessing likelihood increased due to signs of boredom."
        )

    # Mastery outcome
    delta = new_mastery - old_mastery
    if delta > 0.05:
        explanations.append("Student mastery improved significantly.")
    elif delta > 0:
        explanations.append("Student mastery improved gradually.")
    else:
        explanations.append("No mastery improvement observed in this attempt.")

    return {
        "summary": " ".join(explanations),
        "details": {
            "cognitive_state": cognitive_state,
            "base_params": base_params,
            "adapted_params": adapted_params,
            "mastery_change": round(delta, 4)
        }
    }
