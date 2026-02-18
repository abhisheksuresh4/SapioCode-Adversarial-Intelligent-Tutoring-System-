def bkt_update(
    p_L: float,
    correct: bool,
    p_T: float = 0.1,
    p_S: float = 0.1,
    p_G: float = 0.2
) -> float:
    """
    Perform one Bayesian Knowledge Tracing update.

    p_L : prior mastery probability
    correct : True if student answered correctly
    p_T : probability of learning
    p_S : slip probability
    p_G : guess probability
    """

    # Bayesian update
    if correct:
        numerator = p_L * (1 - p_S)
        denominator = numerator + (1 - p_L) * p_G
    else:
        numerator = p_L * p_S
        denominator = numerator + (1 - p_L) * (1 - p_G)

    if denominator == 0:
        posterior = p_L
    else:
        posterior = numerator / denominator

    # Learning transition
    updated_p_L = posterior + (1 - posterior) * p_T

    # Numerical safety
    return min(max(updated_p_L, 0.0), 1.0)
