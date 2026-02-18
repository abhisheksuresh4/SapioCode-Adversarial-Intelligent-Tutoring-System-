def modulate_bkt_params(base_params: dict, cognitive_state: dict) -> dict:
    """
    Adjust BKT parameters using affective state.
    """

    learn = base_params["p_T"]
    slip = base_params["p_S"]
    guess = base_params["p_G"]

    engagement = cognitive_state.get("engagement", 0.0)
    frustration = cognitive_state.get("frustration", 0.0)
    confusion = cognitive_state.get("confusion", 0.0)
    boredom = cognitive_state.get("boredom", 0.0)

    # Apply modulation
    learn *= (1 + engagement * 0.5)
    learn *= (1 - frustration * 0.6)
    slip *= (1 + confusion * 0.7)
    guess *= (1 + boredom * 0.5)
    learn *= (1 - boredom * 0.4)

    # Clamp probabilities
    learn = min(max(learn, 0.01), 0.9)
    slip = min(max(slip, 0.01), 0.9)
    guess = min(max(guess, 0.01), 0.9)

    return {
        "p_T": learn,
        "p_S": slip,
        "p_G": guess
    }
