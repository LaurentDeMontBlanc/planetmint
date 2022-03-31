# Copyright © 2020 Interplanetary Database Association e.V.,
# Planetmint and IPDB software contributors.
# SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
# Code is Apache-2.0 and docs are CC-BY-4.0

import pytest
from planetmint.transactions.types.assets.compose import Compose

def test_asset_compose(b, signed_transfer_tx, user_pk, user_sk):
    tx_compose = Compose.generate()
    tx_compose_signed = tx_compose.sign([user_sk])

    b.store_bulk_transactions([])

    assert tx_compose_signed.validate(b) == tx_compose_signed
    assert tx_compose_signed.asset['id'] == signed_transfer_tx.id

