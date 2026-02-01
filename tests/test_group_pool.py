from escrow_bot.services.group_pool import add_group, add_waitlist, allocate_group, pop_waitlist


def test_group_pool_allocation_and_waitlist():
    add_group(123)
    chat_id = allocate_group("DEAL1")
    assert chat_id == 123
    none_left = allocate_group("DEAL2")
    assert none_left is None
    add_waitlist("DEAL2")
    assert pop_waitlist() == "DEAL2"
