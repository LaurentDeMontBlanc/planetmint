# Copyright © 2020 Interplanetary Database Association e.V.,
# Planetmint and IPDB software contributors.
# SPDX-License-Identifier: (Apache-2.0 AND CC-BY-4.0)
# Code is Apache-2.0 and docs are CC-BY-4.0

"""Query implementation for Tarantool"""
from secrets import token_hex
from operator import itemgetter

import tarantool.error

from planetmint.backend import query
from planetmint.backend.utils import module_dispatch_registrar
from planetmint.backend.tarantool.connection import TarantoolDBConnection
from planetmint.backend.tarantool.transaction.tools import TransactionCompose, TransactionDecompose
from json import dumps, loads

register_query = module_dispatch_registrar(query)


@register_query(TarantoolDBConnection)
def _group_transaction_by_ids(connection, txids: list):
    txspace = connection.get_space("transactions")
    inxspace = connection.get_space("inputs")
    outxspace = connection.get_space("outputs")
    keysxspace = connection.get_space("keys")
    assetsxspace = connection.get_space("assets")
    metaxspace = connection.get_space("meta_data")
    _transactions = []
    for txid in txids:
        _txobject = txspace.select(txid, index="id_search")
        if len(_txobject.data) == 0:
            continue
        _txobject = _txobject.data[0]
        _txinputs = inxspace.select(txid, index="id_search").data
        _txoutputs = outxspace.select(txid, index="id_search").data
        _txkeys = keysxspace.select(txid, index="txid_search").data
        _txassets = assetsxspace.select(txid, index="txid_search").data
        _txmeta = metaxspace.select(txid, index="id_search").data

        _txinputs = sorted(_txinputs, key=itemgetter(6), reverse=False)
        _txoutputs = sorted(_txoutputs, key=itemgetter(8), reverse=False)
        result_map = {
            "transaction": _txobject,
            "inputs": _txinputs,
            "outputs": _txoutputs,
            "keys": _txkeys,
            "asset": _txassets,
            "metadata": _txmeta,
        }
        tx_compose = TransactionCompose(db_results=result_map)
        _transaction = tx_compose.convert_to_dict()
        _transactions.append(_transaction)
    return _transactions


@register_query(TarantoolDBConnection)
def store_transactions(connection, signed_transactions: list):
    for transaction in signed_transactions:
        txprepare = TransactionDecompose(transaction)
        txtuples = txprepare.convert_to_tuple()
        try:
            connection.run(
                connection.space("transactions").insert(txtuples["transactions"]),
                only_data=False
            )
        except:  # This is used for omitting duplicate error in database for test -> test_bigchain_api::test_double_inclusion
            continue

        for _in in txtuples["inputs"]:
            connection.run(
                connection.space("inputs").insert(_in),
                only_data=False
            )

        for _out in txtuples["outputs"]:
            connection.run(
                connection.space("outputs").insert(_out),
                only_data=False
            )

        for _key in txtuples["keys"]:
            connection.run(
                connection.space("keys").insert(_key),
                only_data=False
            )

        if txtuples["metadata"] is not None:
            connection.run(
                connection.space("meta_data").insert(txtuples["metadata"]),
                only_data=False
            )

        if txtuples["asset"] is not None:
            connection.run(
                connection.space("assets").insert(txtuples["asset"]),
                only_data=False
            )


@register_query(TarantoolDBConnection)
def get_transaction(connection, transaction_id: str):
    _transactions = _group_transaction_by_ids(txids=[transaction_id], connection=connection)
    return next(iter(_transactions), None)


@register_query(TarantoolDBConnection)
def get_transactions(connection, transactions_ids: list):
    _transactions = _group_transaction_by_ids(txids=transactions_ids, connection=connection)
    return _transactions


@register_query(TarantoolDBConnection)
def store_metadatas(connection, metadata: list):
    for meta in metadata:
        connection.run(
            connection.space("meta_data").insert(
                (meta["id"], meta["data"] if not "metadata" in meta else meta["metadata"]))
        )


@register_query(TarantoolDBConnection)
def get_metadata(connection, transaction_ids: list):
    _returned_data = []
    for _id in transaction_ids:
        metadata = connection.run(
            connection.space("meta_data").select(_id, index="id_search")
        )
        if metadata is not None:
            if len(metadata) > 0:
                _returned_data.append(metadata)
    return _returned_data if len(_returned_data) > 0 else None


@register_query(TarantoolDBConnection)
def store_asset(connection, asset):
    convert = lambda obj: obj if isinstance(obj, tuple) else (obj, obj["id"], obj["id"])
    try:
        return connection.run(
            connection.space("assets").insert(convert(asset)),
            only_data=False
        )
    except tarantool.error.DatabaseError:
        pass


@register_query(TarantoolDBConnection)
def store_assets(connection, assets: list):
    convert = lambda obj: obj if isinstance(obj, tuple) else (obj, obj["id"], obj["id"])
    for asset in assets:
        try:
            connection.run(
                connection.space("assets").insert(convert(asset)),
                only_data=False
            )
        except tarantool.error.DatabaseError:
            pass


@register_query(TarantoolDBConnection)
def get_asset(connection, asset_id: str):
    _data = connection.run(
        connection.space("assets").select(asset_id, index="txid_search")
    )
    return _data[0][0] if len(_data) > 0 else []


@register_query(TarantoolDBConnection)
def get_assets(connection, assets_ids: list) -> list:
    _returned_data = []
    for _id in list(set(assets_ids)):
        asset = get_asset(connection, _id)
        _returned_data.append(asset)
    return sorted(_returned_data, key=lambda k: k["id"], reverse=False)


@register_query(TarantoolDBConnection)
def get_spent(connection, fullfil_transaction_id: str, fullfil_output_index: str):
    _inputs = connection.run(
        connection.space("inputs").select([fullfil_transaction_id, str(fullfil_output_index)], index="spent_search")
    )
    _transactions = _group_transaction_by_ids(txids=[inp[0] for inp in _inputs], connection=connection)
    return _transactions


@register_query(TarantoolDBConnection)
def get_latest_block(connection):  # TODO Here is used DESCENDING OPERATOR
    _all_blocks = connection.run(
        connection.space("blocks").select()
    )
    block = {"app_hash": '', "height": 0, "transactions": []}

    if _all_blocks is not None:
        if len(_all_blocks) > 0:
            _block = sorted(_all_blocks, key=itemgetter(1), reverse=True)[0]
            _txids = connection.run(
                connection.space("blocks_tx").select(_block[2], index="block_search")
            )
            block["app_hash"] = _block[0]
            block["height"] = _block[1]
            block["transactions"] = [tx[0] for tx in _txids]
        else:
            block = None
    return block


@register_query(TarantoolDBConnection)
def store_block(connection, block: dict):
    block_unique_id = token_hex(8)
    connection.run(
        connection.space("blocks").insert((block["app_hash"],
                                           block["height"],
                                           block_unique_id)),
        only_data=False
    )
    for txid in block["transactions"]:
        connection.run(
            connection.space("blocks_tx").insert((txid, block_unique_id)),
            only_data=False
        )


@register_query(TarantoolDBConnection)
def get_txids_filtered(connection, asset_id: str, operation: str = None,
                       last_tx: any = None):  # TODO here is used 'OR' operator
    actions = {
        "CREATE": {"sets": ["CREATE", asset_id], "index": "transaction_search"},
        # 1 - operation, 2 - id (only in transactions) +
        "TRANSFER": {"sets": ["TRANSFER", asset_id], "index": "transaction_search"},
        # 1 - operation, 2 - asset.id (linked mode) + OPERATOR OR
        None: {"sets": [asset_id, asset_id]}
    }[operation]
    _transactions = []
    if actions["sets"][0] == "CREATE":  # +
        _transactions = connection.run(
            connection.space("transactions").select([operation, asset_id], index=actions["index"])
        )
    elif actions["sets"][0] == "TRANSFER":  # +
        _assets = connection.run(
            connection.space("assets").select([asset_id], index="only_asset_search")
        )
        for asset in _assets:
            _txid = asset[1]
            _transactions = connection.run(
                connection.space("transactions").select([operation, _txid], index=actions["index"])
            )
            if len(_transactions) != 0:
                break
    else:
        _tx_ids = connection.run(
            connection.space("transactions").select([asset_id], index="id_search")
        )
        _assets_ids = connection.run(
            connection.space("assets").select([asset_id], index="only_asset_search")
        )
        return tuple(set([sublist[1] for sublist in _assets_ids] + [sublist[0] for sublist in _tx_ids]))

    if last_tx:
        return tuple(next(iter(_transactions)))

    return tuple([elem[0] for elem in _transactions])


# @register_query(TarantoolDB)
# def text_search(conn, search, *, language='english', case_sensitive=False,
#                 # TODO review text search in tarantool (maybe, remove)
#                 diacritic_sensitive=False, text_score=False, limit=0, table='assets'):
#     cursor = conn.run(
#         conn.collection(table)
#             .find({'$text': {
#             '$search': search,
#             '$language': language,
#             '$caseSensitive': case_sensitive,
#             '$diacriticSensitive': diacritic_sensitive}},
#             {'score': {'$meta': 'textScore'}, '_id': False})
#             .sort([('score', {'$meta': 'textScore'})])
#             .limit(limit))
#
#     if text_score:
#         return cursor
#
#     return (_remove_text_score(obj) for obj in cursor)


def _remove_text_score(asset):
    asset.pop('score', None)
    return asset


@register_query(TarantoolDBConnection)
def get_owned_ids(connection, owner: str):
    _keys = connection.run(
        connection.space("keys").select(owner, index="keys_search")
    )
    if _keys is None or len(_keys) == 0:
        return []
    _transactionids = list(set([key[1] for key in _keys]))
    _transactions = _group_transaction_by_ids(txids=_transactionids, connection=connection)
    return _transactions


@register_query(TarantoolDBConnection)
def get_spending_transactions(connection, inputs):
    _transactions = []

    for inp in inputs:
        _trans_list = get_spent(fullfil_transaction_id=inp["transaction_id"],
                                fullfil_output_index=inp["output_index"],
                                connection=connection)
        _transactions.extend(_trans_list)

    return _transactions


@register_query(TarantoolDBConnection)
def get_block(connection, block_id=[]):
    _block = connection.run(
        connection.space("blocks").select(block_id, index="block_search", limit=1)
    )
    if _block is None or len(_block) == 0:
        return []
    _block = _block[0]
    _txblock = connection.run(
        connection.space("blocks_tx").select(_block[2], index="block_search")
    )
    return {"app_hash": _block[0], "height": _block[1], "transactions": [_tx[0] for _tx in _txblock]}


@register_query(TarantoolDBConnection)
def get_block_with_transaction(connection, txid: str):
    _all_blocks_tx = connection.run(
        connection.space("blocks_tx").select(txid, index="id_search")
    )
    if _all_blocks_tx is None or len(_all_blocks_tx) == 0:
        return []
    _block = connection.run(
        connection.space("blocks").select(_all_blocks_tx[0][1], index="block_id_search")
    )
    return [{"height": _height[1]} for _height in _block]


@register_query(TarantoolDBConnection)
def delete_transactions(connection, txn_ids: list):
    for _id in txn_ids:
        connection.run(connection.space("transactions").delete(_id), only_data=False)
    for _id in txn_ids:
        _inputs = connection.run(connection.space("inputs").select(_id, index="id_search"), only_data=False)
        _outputs = connection.run(connection.space("outputs").select(_id, index="id_search"), only_data=False)
        _keys = connection.run(connection.space("keys").select(_id, index="txid_search"), only_data=False)
        for _kID in _keys:
            connection.run(connection.space("keys").delete(_kID[0], index="id_search"), only_data=False)
        for _inpID in _inputs:
            connection.run(connection.space("inputs").delete(_inpID[5], index="delete_search"), only_data=False)
        for _outpID in _outputs:
            connection.run(connection.space("outputs").delete(_outpID[5], index="unique_search"), only_data=False)

    for _id in txn_ids:
        connection.run(connection.space("meta_data").delete(_id, index="id_search"), only_data=False)

    for _id in txn_ids:
        connection.run(connection.space("assets").delete(_id, index="txid_search"), only_data=False)


@register_query(TarantoolDBConnection)
def store_unspent_outputs(connection, *unspent_outputs: list):
    result = []
    if unspent_outputs:
        for utxo in unspent_outputs:
            output = connection.run(
                connection.space("utxos").insert((utxo['transaction_id'], utxo['output_index'], dumps(utxo)))
            )
            result.append(output)
    return result


@register_query(TarantoolDBConnection)
def delete_unspent_outputs(connection, *unspent_outputs: list):
    result = []
    if unspent_outputs:
        for utxo in unspent_outputs:
            output = connection.run(
                connection.space("utxos").delete((utxo['transaction_id'], utxo['output_index']))
            )
            result.append(output)
    return result


@register_query(TarantoolDBConnection)
def get_unspent_outputs(connection, query=None):  # for now we don't have implementation for 'query'.
    _utxos = connection.run(
        connection.space("utxos").select([])
    )
    return [loads(utx[2]) for utx in _utxos]


@register_query(TarantoolDBConnection)
def store_pre_commit_state(connection, state: dict):
    _precommit = connection.run(
        connection.space("pre_commits").select(state["height"], index="height_search", limit=1)
    )
    unique_id = token_hex(8) if _precommit is None or len(_precommit.data) == 0 else _precommit.data[0][0]
    connection.run(
        connection.space("pre_commits").upsert((unique_id, state["height"], state["transactions"]),
                                               op_list=[('=', 0, unique_id),
                                                        ('=', 1, state["height"]),
                                                        ('=', 2, state["transactions"])],
                                               limit=1),
        only_data=False
    )


@register_query(TarantoolDBConnection)
def get_pre_commit_state(connection):
    _commit = connection.run(
        connection.space("pre_commits").select([], index="id_search")
    )
    if _commit is None or len(_commit) == 0:
        return None
    _commit = sorted(_commit, key=itemgetter(1), reverse=True)[0]
    return {"height": _commit[1], "transactions": _commit[2]}


@register_query(TarantoolDBConnection)
def store_validator_set(conn, validators_update: dict):
    _validator = conn.run(
        conn.space("validators").select(validators_update["height"], index="height_search", limit=1)
    )
    unique_id = token_hex(8) if _validator is None or len(_validator) == 0 else _validator.data[0][0]
    conn.run(
        conn.space("validators").upsert((unique_id, validators_update["height"], validators_update["validators"]),
                                        op_list=[('=', 0, unique_id),
                                                 ('=', 1, validators_update["height"]),
                                                 ('=', 2, validators_update["validators"])],
                                        limit=1),
        only_data=False
    )


@register_query(TarantoolDBConnection)
def delete_validator_set(connection, height: int):
    _validators = connection.run(
        connection.space("validators").select(height, index="height_search")
    )
    for _valid in _validators:
        connection.run(
            connection.space("validators").delete(_valid[0]),
            only_data=False
        )


@register_query(TarantoolDBConnection)
def store_election(connection, election_id: str, height: int, is_concluded: bool):
    connection.run(
        connection.space("elections").upsert((election_id, height, is_concluded),
                                             op_list=[('=', 0, election_id),
                                                      ('=', 1, height),
                                                      ('=', 2, is_concluded)],
                                             limit=1),
        only_data=False
    )


@register_query(TarantoolDBConnection)
def store_elections(connection, elections: list):
    for election in elections:
        _election = connection.run(
            connection.space("elections").insert((election["election_id"],
                                                  election["height"],
                                                  election["is_concluded"])),
            only_data=False
        )


@register_query(TarantoolDBConnection)
def delete_elections(connection, height: int):
    _elections = connection.run(
        connection.space("elections").select(height, index="height_search")
    )
    for _elec in _elections:
        connection.run(
            connection.space("elections").delete(_elec[0]),
            only_data=False
        )


@register_query(TarantoolDBConnection)
def get_validator_set(connection, height: int = None):
    _validators = connection.run(
        connection.space("validators").select()
    )
    if height is not None and _validators is not None:
        _validators = [{"height": validator[1], "validators": validator[2]} for validator in _validators if
                       validator[1] <= height]
        return next(iter(sorted(_validators, key=lambda k: k["height"], reverse=True)), None)
    elif _validators is not None:
        _validators = [{"height": validator[1], "validators": validator[2]} for validator in _validators]
        return next(iter(sorted(_validators, key=lambda k: k["height"], reverse=True)), None)
    return None


@register_query(TarantoolDBConnection)
def get_election(connection, election_id: str):
    _elections = connection.run(
        connection.space("elections").select(election_id, index="id_search")
    )
    if _elections is None or len(_elections) == 0:
        return None
    _election = sorted(_elections, key=itemgetter(0), reverse=True)[0]
    return {"election_id": _election[0], "height": _election[1], "is_concluded": _election[2]}


@register_query(TarantoolDBConnection)
def get_asset_tokens_for_public_key(connection, asset_id: str,
                                    public_key: str):  # FIXME Something can be wrong with this function ! (public_key) is not used
    # space = connection.space("keys")
    # _keys = space.select([public_key], index="keys_search")
    _transactions = connection.run(
        connection.space("assets").select([asset_id], index="assetid_search")
    )
    # _transactions = _transactions
    # _keys = _keys.data
    _grouped_transactions = _group_transaction_by_ids(connection=connection, txids=[_tx[1] for _tx in _transactions])
    return _grouped_transactions


@register_query(TarantoolDBConnection)
def store_abci_chain(connection, height: int, chain_id: str, is_synced: bool = True):
    connection.run(
        connection.space("abci_chains").upsert((height, is_synced, chain_id),
                                               op_list=[('=', 0, height),
                                                        ('=', 1, is_synced),
                                                        ('=', 2, chain_id)],
                                               limit=1),
        only_data=False
    )


@register_query(TarantoolDBConnection)
def delete_abci_chain(connection, height: int):
    _chains = connection.run(
        connection.space("abci_chains").select(height, index="height_search")
    )
    for _chain in _chains:
        connection.run(
            connection.space("abci_chains").delete(_chain[2]),
            only_data=False
        )


@register_query(TarantoolDBConnection)
def get_latest_abci_chain(connection):
    _all_chains = connection.run(
        connection.space("abci_chains").select()
    )
    if _all_chains is None or len(_all_chains) == 0:
        return None
    _chain = sorted(_all_chains, key=itemgetter(0), reverse=True)[0]
    return {"height": _chain[0], "is_synced": _chain[1], "chain_id": _chain[2]}
