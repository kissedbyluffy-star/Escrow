from escrow_bot.utils.captcha import generate_challenge


def test_captcha_challenge():
    challenge = generate_challenge()
    assert challenge.correct in challenge.options
    assert len(challenge.options) == 4
