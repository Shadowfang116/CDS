from app.services.canonical_docs import classify_document_type


def test_development_charges_resolution_maps_to_dues_clearance():
    classified, source = classify_document_type(
        "",
        "ترقیاتی واجبات کلیئرنس سرٹیفکیٹ\nNOC میں ظاہر کردہ واجبات کی ادائیگی\nرقم PKR 1,850,000 CLEARED",
    )

    assert (classified, source) == ("Dues Clearance", "content")


def test_prior_charge_release_maps_to_charge_release():
    classified, source = classify_document_type(
        "",
        "سابقہ چارج / رہن کی رہائی و اطمینان کا خط\nPrior encumbrance resolution\nCHG-T-2019-77 released/satisfied",
    )

    assert (classified, source) == ("Charge Release", "content")


def test_identity_confirmation_does_not_map_to_mutation():
    classified, source = classify_document_type(
        "",
        "نام / قانونی شناخت کی تصدیق\nکمپنی نام کے املا کے فرق کی reconciliation evidence\nIdentity Confirmation",
    )

    assert (classified, source) == ("Identity Confirmation", "content")
