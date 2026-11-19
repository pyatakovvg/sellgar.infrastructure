#!/usr/bin/env python3
"""Initialize dev Store from retained published owner events and configure RUB.

Usage: initialize-store.py /path/to/kubectl --kubeconfig /path/to/kubeconfig
No host data is imported; no source outbox rows or business tables are modified.
"""
import json
import subprocess
import sys

kubectl = sys.argv[1:]
if not kubectl:
    raise SystemExit(__doc__)

namespace = "sellgar-dev"
ready = subprocess.check_output(
    [*kubectl, "-n", namespace, "get", "deployment", "store-service", "-o", "json"],
    text=True,
)
if not any(
    condition["type"] == "Available" and condition["status"] == "True"
    for condition in json.loads(ready).get("status", {}).get("conditions", [])
):
    raise SystemExit("Store must be available before its initial projection replay")

replay = r"""
const {Client} = require('pg');
const amqp = require('amqplib');
const product = process.argv[1] === 'product';
const env = process.env;
const prefix = product ? 'PRODUCT_' : '';
const database = new Client({
  host: env[prefix + 'DATABASE_HOST'], port: Number(env[prefix + 'DATABASE_PORT']),
  user: env[prefix + 'DATABASE_USERNAME'], password: env[prefix + 'DATABASE_PASSWORD'],
  database: env[product ? 'PRODUCT_DATABASE_NAME' : 'DATABASE_DATABASE_NAME'],
});
const aggregateType = product ? 'product' : 'shop';
(async () => {
  let broker;
  try {
    await database.connect();
    const {rows} = await database.query(`SELECT uuid, producer, aggregate_type,
      aggregate_id, aggregate_version, event_type, schema_version, payload, occurred_at
      FROM outbox_event WHERE published_at IS NOT NULL AND aggregate_type = $1
      ORDER BY aggregate_id, aggregate_version`, [aggregateType]);
    const versions = new Map();
    for (const row of rows) {
      const expected = (versions.get(row.aggregate_id) ?? 0) + 1;
      if (Number(row.aggregate_version) !== expected) throw new Error('Retained outbox history is incomplete');
      versions.set(row.aggregate_id, expected);
    }
    broker = await amqp.connect(product ? env.PRODUCT_AMQP_URL : {
      hostname: env.AMQP_HOSTNAME, port: Number(env.AMQP_PORT),
      username: env.AMQP_USERNAME, password: env.AMQP_PASSWORD,
    });
    const channel = await broker.createConfirmChannel();
    await channel.checkQueue('store_srv.event.queue');
    for (const row of rows) {
      const data = {eventUuid: row.uuid, producer: row.producer, aggregateType: row.aggregate_type,
        aggregateId: row.aggregate_id, aggregateVersion: Number(row.aggregate_version),
        eventType: row.event_type, schemaVersion: row.schema_version,
        payload: row.payload, occurredAt: row.occurred_at};
      channel.sendToQueue('store_srv.event.queue', Buffer.from(JSON.stringify({pattern: row.event_type, data})),
        {persistent: true});
    }
    await channel.waitForConfirms();
    console.log(`Confirmed ${rows.length} retained ${aggregateType} events to the Store queue`);
  } finally {
    if (broker) await broker.close();
    await database.end();
  }
})().catch(error => { console.error(error.name); process.exitCode = 1; });
"""

for deployment, owner in [("shop-service", "shop"), ("product-service", "product")]:
    subprocess.run(
        [*kubectl, "-n", namespace, "exec", f"deployment/{deployment}", "--", "node",
         "--env-file=.env", "-e", replay, owner],
        check=True,
    )

currency = r"""
const {ClientProxyFactory, Transport} = require('@nestjs/microservices');
const {firstValueFrom, timeout} = require('rxjs');
const client = ClientProxyFactory.create({transport: Transport.RMQ, options: {
  urls: [{hostname: process.env.AMQP_HOSTNAME, port: Number(process.env.AMQP_PORT),
    username: process.env.AMQP_USERNAME, password: process.env.AMQP_PASSWORD}],
  queue: process.env.AMQP_STORE_SRV_COMMAND_QUEUE, queueOptions: {durable: true},
}});
const request = (cmd, data) => firstValueFrom(client.send({cmd}, data).pipe(timeout(10000)));
(async () => {
  try {
    const currencies = await request('currency.findAll', {});
    if (!currencies.data.some(currency => currency.code === 'RUB')) {
      await request('currency.create', {code: 'RUB', value: 'Российский рубль', order: 0});
      console.log('Created development currency RUB');
    } else console.log('Preserved development currency RUB');
  } finally { await client.close(); }
})().catch(error => { console.error(error.name); process.exitCode = 1; });
"""
subprocess.run(
    [*kubectl, "-n", namespace, "exec", "deployment/store-service", "--", "node", "--env-file=.env", "-e", currency],
    check=True,
)
