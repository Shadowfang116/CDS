from app.services.next_action import rank_next_action


def test_hard_stop_outranks_unconfirmed_field() -> None:
    assert (
        rank_next_action(
            open_hard_stop_title="TITLE CHAIN BREAK",
            unconfirmed_key_field="Borrower name",
        )
        == "Clear hard-stop: TITLE CHAIN BREAK"
    )


def test_pack_is_last() -> None:
    assert rank_next_action(pack_hint="Submit for approval") == "Submit for approval"
