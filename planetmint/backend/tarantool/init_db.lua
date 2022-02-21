abci_chains = box.schema.space.create('abci_chains',{engine = 'memtx' , is_sync = false})
abci_chains:format({{name='height' , type='integer'},{name='is_synched' , type='boolean'},{name='chain_id',type='string'}})
abci_chains:create_index('id_search' ,{type='hash', parts={'chain_id'}})
abci_chains:create_index('height_search' ,{type='tree',unique=false, parts={'height'}})

assets = box.schema.space.create('assets' , {engine='memtx' , is_sync=false})
assets:format({{name='asset_id', type='string'}, {name='data' , type='any'}})
assets:create_index('assetid_search', {type='hash', parts={'asset_id'}})

blocks = box.schema.space.create('blocks' , {engine='memtx' , is_sync=false})
blocks:format{{name='app_hash',type='string'},{name='height' , type='integer'},{name='block_id' , type='string'}}
blocks:create_index('id_search' , {type='hash' , parts={'block_id'}})
blocks:create_index('block_search' , {type='tree', unique = false, parts={'height'}})
blocks:create_index('block_id_search', {type = 'hash', parts ={'block_id'}})

blocks_tx = box.schema.space.create('blocks_tx')
blocks_tx:format{{name='transaction_id', type = 'string'}, {name = 'block_id', type = 'string'}}
blocks_tx:create_index('id_search',{ type = 'hash', parts={'transaction_id'}})
blocks_tx:create_index('block_search', {type = 'tree',unique=false, parts={'block_id'}})

elections = box.schema.space.create('elections',{engine = 'memtx' , is_sync = false})
elections:format({{name='election_id' , type='string'},{name='height' , type='integer'}, {name='is_concluded' , type='boolean'}})
elections:create_index('id_search' , {type='hash', parts={'election_id'}})
elections:create_index('height_search' , {type='tree',unique=false, parts={'height'}})
elections:create_index('update_search', {type='tree', unique=false, parts={'election_id', 'height'}})

meta_datas = box.schema.space.create('meta_data',{engine = 'memtx' , is_sync = false})
meta_datas:format({{name='transaction_id' , type='string'}, {name='meta_data' , type='any'}})
meta_datas:create_index('id_search', { type='hash' , parts={'transaction_id'}})

pre_commits = box.schema.space.create('pre_commits' , {engine='memtx' , is_sync=false})
pre_commits:format({{name='commit_id', type='string'}, {name='height',type='integer'}, {name='transactions',type=any}})
pre_commits:create_index('id_search', {type ='hash' , parts={'commit_id'}})
pre_commits:create_index('height_search', {type ='tree',unique=false, parts={'height'}})

validators = box.schema.space.create('validators' , {engine = 'memtx' , is_sync = false})
validators:format({{name='validator_id' , type='string'},{name='height',type='integer'},{name='validators' , type='any'}})
validators:create_index('id_search' , {type='hash' , parts={'validator_id'}})
validators:create_index('height_search' , {type='tree', unique=false, parts={'height'}})

transactions = box.schema.space.create('transactions',{engine='memtx' , is_sync=false})
transactions:format({{name='transaction_id' , type='string'}, {name='operation' , type='string'}, {name='version' ,type='string'}, {name='asset_id', type='string'}})
transactions:create_index('id_search' , {type = 'hash' , parts={'transaction_id'}})
transactions:create_index('only_asset_search', {type = 'tree', unique=false, parts={'asset_id'}})
transactions:create_index('asset_search' , {type = 'tree',unique=false, parts={'operation', 'asset_id'}})
transactions:create_index('transaction_search' , {type = 'tree',unique=false, parts={'operation', 'transaction_id'}})
transactions:create_index('both_search' , {type = 'tree',unique=false, parts={'asset_id', 'transaction_id'}})

inputs = box.schema.space.create('inputs')
inputs:format({{name='transaction_id' , type='string'}, {name='fulfillment' , type='string'}, {name='owners_before' , type='array'}, {name='fulfills_transaction_id', type = 'string'}, {name='fulfills_output_index', type = 'string'}, {name='input_id', type='string'}})
inputs:create_index('spent_search' , {type = 'hash', parts={'fulfills_transaction_id', 'fulfills_output_index'}})
inputs:create_index('delete_search' , {type = 'hash', parts={'input_id'}})
inputs:create_index('id_search', {type = 'tree', unique=false, parts = {'transaction_id'}})

outputs = box.schema.space.create('outputs')
outputs:format({{name='transaction_id' , type='string'}, {name='amount' , type='string'}, {name='uri', type='string'}, {name='details_type', type='string'}, {name='details_public_key', type='string'}, {name = 'output_id', type = 'string'}})
outputs:create_index('unique_search' ,{type='hash', parts={'output_id'}})
outputs:create_index('id_search' ,{type='tree', unique=false, parts={'transaction_id'}})

keys = box.schema.space.create('keys')
keys:format({{name = 'transaction_id', type = 'string'} ,{name = 'output_id', type = 'string'}, {name = 'public_key', type = 'string'}})
keys:create_index('keys_search', {type = 'hash', parts={'public_key'}})
keys:create_index('txid_search', {type = 'tree', unique=false, parts={'transaction_id'}})
keys:create_index('id_search', {type = 'tree', unique=false, parts={'output_id'}})

local console = require('console')
console.start()