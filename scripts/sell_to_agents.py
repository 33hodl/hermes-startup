#!/usr/bin/env python3
"""One-command 'sell to agents' template for a Hermes-built store.

Generates a complete, deployable merchant endpoint that speaks the Agentic
Commerce Protocol (ACP, agenticcommerce.dev — the OpenAI + Stripe open
checkout standard): agents can create, retrieve, update, complete, and cancel
checkout sessions against your store, and payment is taken through Stripe
hosted Checkout, the same pattern Hermes Startup itself runs.

Usage (one command):

    python3 scripts/sell_to_agents.py new ./my-store

That writes everything into ./my-store:

    README.md                 deploy + test instructions, honest framing
    products.json             your catalog (edit this)
    for-agents.md             agent-readable pay/use contract
    checkout_sessions.js      the ACP merchant Worker (create/get/update/
                              complete/cancel on /checkout_sessions)
    checkout_sessions.test.mjs  self-test (node --test checkout_sessions.test.mjs)
                                covers ACP checkout + Ed25519 signed receipts
    package.json              {"type": "module"} so the test and Worker run directly
    wrangler.toml.example     Workers deploy config (copy to wrangler.toml)

The generated code is fail-closed: unknown products and oversize quantities are
rejected, totals are always recomputed from the catalog (never from the
request), payment without a configured restricted Stripe key is refused with a
422, and completion always returns the order plus a hosted checkout URL.

Security notes:
- Set AGENT_API_KEY (any strong bearer secret) at deploy time; until then the
  endpoint accepts unauthenticated sessions, which is fine for a public
  storefront but not for one that moves real money.
- Set STRIPE_SECRET to a RESTRICTED Stripe key (Checkout Sessions write only).
- Never put live keys in code, chat, or version control.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

API_VERSION = "2026-04-17"

README = """# Sell to agents (ACP store)

This folder is a complete merchant endpoint for the Agentic Commerce Protocol
(ACP, agenticcommerce.dev, the open checkout standard maintained by OpenAI and
Stripe). Any ACP-compatible agent can create a checkout session, update it, and
complete the purchase. Payment runs through Stripe hosted Checkout, the same
pattern Hermes Startup uses on its own product.

## What you have

- `products.json` — your catalog. This is the only file you edit.
- `checkout_sessions.js` — the ACP Worker. It implements:
  - `POST /checkout_sessions` (create, requires `Idempotency-Key`)
  - `GET  /checkout_sessions/{id}` (retrieve)
  - `POST /checkout_sessions/{id}` (update)
  - `POST /checkout_sessions/{id}/complete` (pay + create order)
  - `POST /checkout_sessions/{id}/cancel`
  - `GET  /receipts/key` (public Ed25519 public key, no auth)
  - `POST /receipts/verify` (public: check any receipt, no auth)
  - `GET  /receipts/{order_id}` (public: refetch a receipt, no auth)
- `checkout_sessions.test.mjs` — run `node --test checkout_sessions.test.mjs`
  to prove the endpoint behaves before you deploy.
- `for-agents.md` — the agent-readable contract for your store.
- `wrangler.toml.example` — copy to `wrangler.toml` and fill in.

## One-command flow

1. Edit `products.json`: id, name, price in cents, currency, description.
2. Get a restricted Stripe key (Dashboard -> Developers -> API keys ->
   restricted key; Checkout Sessions write, everything else none).
3. Deploy with wrangler or any Cloudflare Worker/Pages host.
4. Set your secrets, then run the self-test, then do one real test purchase.

## Deploy (Workers)

    cp wrangler.toml.example wrangler.toml   # set STORE_ORIGIN + name
    npx wrangler secret put STRIPE_SECRET
    npx wrangler secret put AGENT_API_KEY
    npx wrangler deploy
    curl https://<your-worker>/.well-known/acp   # health: 200

## Test it

    node --test checkout_sessions.test.mjs
    # then, once deployed:
    curl -i -X POST https://<your-worker>/checkout_sessions \\
      -H 'content-type: application/json' \\
      -H 'Idempotency-Key: test-1' \\
      -H 'API-Version: 2026-04-17' \\
      -d '{"line_items":[{"id":"starter","quantity":1}],"currency":"usd"}'

## Signed receipts (the part buyers cannot fake)

With `RECEIPT_ED25519_PRIVATE_KEY` and `RECEIPT_ED25519_PUBLIC_JWK` set, every
completed order carries `order.receipt`: a detached Ed25519 signature over the
order id, line items, total, currency, and optional `deliverable_sha256`. Any
agent can verify it with `GET /receipts/key` and no API key, so "the store
acknowledged this order at this price, and this is the artifact hash" stops
being a screenshot.

Generate a key pair once:

    node -e "const {generateKeyPairSync}=require('node:crypto');const {publicKey,privateKey}=generateKeyPairSync('ed25519');console.log('PRIVATE='+privateKey.export({format:'der',type:'pkcs8'}).toString('base64'));console.log('JWK='+JSON.stringify(publicKey.export({format:'jwk'})))"

    npx wrangler secret put RECEIPT_ED25519_PRIVATE_KEY   # paste PRIVATE
    # add JWK as a plain-text var in wrangler.toml [vars], e.g.
    # RECEIPT_ED25519_PUBLIC_JWK = '{"kty":"OKP",...}'

Bind the artifact you deliver so the receipt covers it too: send
`{"fulfillment_details": {"deliverable_sha256": "<64 hex>"}}` on complete.
Unset keys mean `receipt: null`; nothing is ever signed with a placeholder key.

The receipt attests the order, price, and artifact hash. It does not claim the
card charge settled: Stripe's webhook remains the payment truth, which is why
the payload says `payment_status: "pending_hosted_checkout"`.

## Honest framing

An ACP endpoint makes your store addressable by agents that implement ACP
(OpenAI's ChatGPT is the first platform). Listing on a specific agent platform
is a separate application handled by that platform. The endpoint removes
friction for agents that are already trying to buy; it does not create demand.
No income, outcome, or placement promise is implied by deploying it.
"""

PRODUCTS_JSON = {
    "products": [
        {
            "id": "starter",
            "name": "Starter pack",
            "unit_amount": 1000,
            "currency": "usd",
            "description": "Replace this with your offer. Price is in cents.",
            "images": [],
            "max_quantity": 10,
            "availability_status": "in_stock",
        },
        {
            "id": "premium",
            "name": "Premium pack",
            "unit_amount": 2500,
            "currency": "usd",
            "description": "A second offer. Remove or extend as you like.",
            "images": [],
            "max_quantity": 3,
            "availability_status": "in_stock",
        },
    ]
}

FOR_AGENTS_MD = """# Buying from this store (for agents)

This store speaks the Agentic Commerce Protocol (ACP). To buy on a human's
behalf, run the standard ACP checkout flow:

1. `POST /checkout_sessions` with `{"line_items":[{"id":"<product_id>",
   "quantity": N}], "currency": "usd"}`. Send an `Idempotency-Key` header
   (opaque string, 1-255 chars) and `API-Version: 2026-04-17`. The response is
   the authoritative cart state: line items, totals in cents, fulfillment
   options, messages, and capabilities. Totals are computed by the store, not
   by the agent; never quote a number the store did not return.
2. If the buyer is ready, complete: `POST /checkout_sessions/{id}/complete`
   with `{"buyer": {"email": "..."}, "payment_data": {"token": "hosted_checkout",
   "provider": "stripe"}}`. The store creates a Stripe hosted Checkout session.
3. The response marks the session `completed` and returns an `order` plus
   `continue_url`. That URL is the payment page for the human buyer. Hand it
   to the buyer; payment confirmation arrives through the Stripe webhook the
   merchant configured, not from this endpoint.
4. If `order.receipt` is present, it is an Ed25519 signature over the order
   id, line items, total, currency, and `deliverable_sha256`. Verify it offline
   with the JWK from `GET /receipts/key`, or POST it to `/receipts/verify`.
   Both are public. A receipt proves the store acknowledged this exact order at
   this price; it does not prove the card was charged (`payment_status` will say
   `pending_hosted_checkout` until the merchant's webhook confirms).
   Offline alternative, no HTTP: sign/verify the canonical JSON of `payload` —
   recursively sorted keys, no whitespace, arrays in order — as UTF-8 bytes with
   Ed25519, signature base64url unpadded. Any conforming library agrees; nothing
   about verification depends on this Worker being reachable.

Rules the store enforces (fail-closed):

- Unknown product ids are rejected (422). Never invent ids.
- Quantity per line is capped (see `max_quantity` in products.json).
- Prices always come from the catalog, never from the agent request.
- `Complete` without a configured payment key is refused (422), and the
  merchant may require a `Bearer` token set via `AGENT_API_KEY`.
- `Idempotency-Key` is required on every POST. Replay with the same key and
  body returns the same session; a different body under the same key is a 409.
"""

WRANGLER_TOML = """name = "my-acp-store"
main = "checkout_sessions.js"
compatibility_date = "2026-01-01"

# Where your store lives (used for Stripe success/cancel URLs).
# [vars]
# STORE_ORIGIN = "https://your-store.example"

# Secrets (use `npx wrangler secret put NAME`):
#   STRIPE_SECRET  restricted Stripe key, Checkout Sessions write only
#   AGENT_API_KEY  any strong bearer secret; undefined = unauthenticated
#   RECEIPT_ED25519_PRIVATE_KEY  base64 PKCS#8 Ed25519 key (see README)
# Public vars ([vars], safe to publish):
#   RECEIPT_ED25519_PUBLIC_JWK   the matching public JWK, JSON
#   RECEIPT_KEY_ID               optional label, defaults to "default"
"""

PACKAGE_JSON = {"name": "acp-store", "private": True, "type": "module"}

WORKER_JS = r"""// ACP merchant endpoint for one store (Agentic Commerce Protocol, 2026-04-17).
// Emits create / retrieve / update / complete / cancel on /checkout_sessions.
// Fail-closed by design: prices are server-side only, sessions are
// idempotent, and payment requires a configured restricted Stripe key.

const API_VERSION = '2026-04-17';

// Sessions and idempotency live in memory. For multi-instance or durable
// storage, point env.SESSIONS at a Cloudflare KV binding with get/put;
// this file prefers that binding when present.
const memory = new Map(); // id -> session
const idem = new Map();   // idempotency key -> {body, result, status}

function nowIso() {
  return new Date().toISOString();
}

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers },
  });
}

function protocolError(code, message, param, status = 422) {
  const error = { type: 'invalid_request', code, message };
  if (param) error.param = param;
  return json(error, status);
}

function makeId(prefix) {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, '').slice(0, 24)}`;
}

// --- Signed receipts (Ed25519) ----------------------------------------------
// A receipt is a detached Ed25519 signature over a canonical JSON payload, so
// any agent can prove THIS store acknowledged THIS order at THIS price without
// trusting a screenshot or calling back into a database it cannot see.
// Configure RECEIPT_ED25519_PRIVATE_KEY (base64 PKCS#8) plus
// RECEIPT_ED25519_PUBLIC_JWK (JSON Web Key). With neither set, orders carry
// receipt: null and no signature is ever faked.
const orders = new Map(); // order id -> order (for GET /receipts/{order_id})

const b64Alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

function base64ToBytes(value) {
  const normalized = String(value).replace(/-/g, '+').replace(/_/g, '/').replace(/=+$/, '');
  const bytes = [];
  let buffer = 0;
  let bits = 0;
  for (const char of normalized) {
    const index = b64Alphabet.indexOf(char);
    if (index < 0) throw new Error('invalid base64');
    buffer = (buffer << 6) | index;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes.push((buffer >> bits) & 0xff);
    }
  }
  return new Uint8Array(bytes);
}

function bytesToBase64Url(bytes) {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i];
    const b = i + 1 < bytes.length ? bytes[i + 1] : 0;
    const c = i + 2 < bytes.length ? bytes[i + 2] : 0;
    const triple = (a << 16) | (b << 8) | c;
    out += b64Alphabet[(triple >> 18) & 63] + b64Alphabet[(triple >> 12) & 63];
    if (i + 1 < bytes.length) out += b64Alphabet[(triple >> 6) & 63];
    if (i + 2 < bytes.length) out += b64Alphabet[triple & 63];
  }
  return out.replace(/\+/g, '-').replace(/\//g, '_');
}

// Deterministic JSON: sorted keys, no incidental whitespace. The signed bytes
// must not depend on how a runtime happens to order object properties.
function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  const keys = Object.keys(value).filter((k) => value[k] !== undefined).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canonicalJson(value[k])).join(',') + '}';
}

async function importReceiptKeys(env) {
  if (!env.RECEIPT_ED25519_PRIVATE_KEY || !env.RECEIPT_ED25519_PUBLIC_JWK) return null;
  const privateKey = await crypto.subtle.importKey(
    'pkcs8',
    base64ToBytes(env.RECEIPT_ED25519_PRIVATE_KEY),
    { name: 'Ed25519' },
    false,
    ['sign'],
  );
  const publicJwk = JSON.parse(env.RECEIPT_ED25519_PUBLIC_JWK);
  const publicKey = await crypto.subtle.importKey('jwk', publicJwk, { name: 'Ed25519' }, false, ['verify']);
  return { privateKey, publicKey };
}

async function signReceipt(env, payload) {
  let keys;
  try {
    keys = await importReceiptKeys(env);
  } catch {
    throw new ProtocolFailure('receipt_key_invalid', 'Receipt signing key is malformed', null, 500);
  }
  if (!keys) return null;
  const signature = await crypto.subtle.sign(
    { name: 'Ed25519' },
    keys.privateKey,
    new TextEncoder().encode(canonicalJson(payload)),
  );
  const origin = env.STORE_ORIGIN || '';
  return {
    alg: 'Ed25519',
    key_id: env.RECEIPT_KEY_ID || 'default',
    payload,
    signature: bytesToBase64Url(new Uint8Array(signature)),
    key_url: origin + '/receipts/key',
  };
}

async function verifyReceipt(env, receipt) {
  if (!receipt || typeof receipt !== 'object' || !receipt.payload || !receipt.signature) return false;
  let keys;
  try {
    keys = await importReceiptKeys(env);
  } catch {
    return false;
  }
  if (!keys) return false;
  try {
    const signature = base64ToBytes(receipt.signature);
    return await crypto.subtle.verify(
      { name: 'Ed25519' },
      keys.publicKey,
      signature,
      new TextEncoder().encode(canonicalJson(receipt.payload)),
    );
  } catch {
    return false;
  }
}

function bearer(request, env) {
  if (!env.AGENT_API_KEY) return true; // dev storefront: no auth configured
  const auth = request.headers.get('authorization') || '';
  return auth === `Bearer ${env.AGENT_API_KEY}`;
}

function requiredPostHeaders(request) {
  if (request.method === 'POST') {
    const idemKey = request.headers.get('idempotency-key') || '';
    if (!idemKey || idemKey.length > 255) {
      return { error: protocolError('idempotency_key_required', 'Idempotency-Key header is required (1-255 chars)', null, 400) };
    }
    const apiVersion = request.headers.get('api-version') || '';
    if (!apiVersion) {
      return { error: protocolError('api_version_required', 'API-Version header is required', null, 400) };
    }
  }
  return {};
}

async function readJson(request) {
  const text = await request.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

async function catalog(env, request) {
  if (env.PRODUCTS_JSON) return JSON.parse(env.PRODUCTS_JSON);
  const origin = env.STORE_ORIGIN || new URL(request.url).origin;
  const res = await fetch(`${origin}/products.json`, { headers: { accept: 'application/json' } });
  if (!res.ok) {
    throw new ProtocolFailure('service_unavailable', 'catalog_unavailable', 'Catalog could not be loaded', 503);
  }
  return res.json();
}

class ProtocolFailure extends Error {
  constructor(code, message, param, status = 422) {
    super(message);
    this.code = code;
    this.param = param;
    this.status = status;
  }
}

function productIndex(catalogJson) {
  const index = new Map();
  for (const product of catalogJson.products || []) index.set(product.id, product);
  return index;
}

// Build authoritative line items and totals from the catalog.
// Request quantity is the only client input that is honored; price, currency,
// and availability always come from the catalog.
function buildCart(catalogJson, requested, currency) {
  const index = productIndex(catalogJson);
  const items = requested || [];
  if (!Array.isArray(items) || items.length === 0) {
    throw new ProtocolFailure('empty_cart', 'line_items must contain at least one item', '$.line_items');
  }
  const lineItems = [];
  let subtotal = 0;
  for (const entry of items) {
    const id = entry && entry.id;
    const quantity = entry && entry.quantity;
    const product = id ? index.get(id) : undefined;
    if (!product) {
      throw new ProtocolFailure('product_not_found', `Unknown product id: ${String(id)}`, '$.line_items[*].id');
    }
    const maxQuantity = Number(product.max_quantity) || 10;
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > maxQuantity) {
      throw new ProtocolFailure('quantity_invalid', `Quantity for ${id} must be an integer between 1 and ${maxQuantity}`, '$.line_items[*].quantity');
    }
    const unitAmount = Number(product.unit_amount);
    const amount = unitAmount * quantity;
    subtotal += amount;
    lineItems.push({
      id: `${id}-${quantity}`,
      item: {
        id,
        name: product.name,
        description: product.description || '',
        images: product.images || [],
      },
      quantity,
      name: product.name,
      unit_amount: unitAmount,
      product_id: id,
      availability_status: product.availability_status || 'in_stock',
      totals: [
        { label: 'subtotal', currency, amount },
        { label: 'total', currency, amount },
      ],
    });
  }
  return {
    lineItems,
    totals: [
      { label: 'subtotal', currency, amount: subtotal },
      { label: 'total', currency, amount: subtotal },
    ],
  };
}

function capabilitiesBlock() {
  return {
    payment: {
      handlers: [
        {
          id: 'hosted_checkout',
          name: 'dev.acp.hosted.checkout',
          version: API_VERSION,
          display_name: 'Card (Stripe hosted Checkout)',
          requires_delegate_payment: false,
          requires_pci_compliance: false,
          psp: 'stripe',
          config: {},
        },
      ],
    },
    interventions: {
      supported: [],
      required: [],
      enforcement: 'optional',
      display_context: 'redirect',
      redirect_context: 'external_browser',
      max_redirects: 1,
    },
  };
}

function linksBlock(env) {
  const origin = env.STORE_ORIGIN || 'https://your-store.example';
  return [
    { name: 'Terms', url: `${origin}/terms` },
    { name: 'Support', url: `mailto:you@${new URL(origin).hostname || 'example.com'}` },
  ];
}

function sessionEnvelope(session, order) {
  const body = { ...session };
  if (order) body.order = order;
  return body;
}

async function createSession(request, env, parsed) {
  const currency = parsed.currency || 'usd';
  const cart = buildCart(await catalog(env, request), parsed.line_items, currency);
  const now = nowIso();
  const session = {
    id: makeId('cs'),
    protocol: { name: 'agentic_checkout', version: API_VERSION },
    capabilities: capabilitiesBlock(),
    status: 'ready_for_payment',
    currency,
    line_items: cart.lineItems,
    totals: cart.totals,
    fulfillment_options: [],
    messages: [{ type: 'info', code: 'hosted_checkout', message: 'Complete checkout to receive a Stripe hosted payment page.' }],
    links: linksBlock(env),
    created_at: now,
    updated_at: now,
    expires_at: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
    continue_url: null,
  };
  await putSession('cs', session);
  return json(sessionEnvelope(session), 201);
}

function findSession(id) {
  return memory.get(id);
}

async function putSession(kind, session) {
  if (kind === 'cs') memory.set(session.id, session);
}

async function handleComplete(request, env, parsed, session) {
  const paymentData = parsed.payment_data;
  if (!paymentData || typeof paymentData !== 'object') {
    throw new ProtocolFailure('payment_data_required', 'payment_data is required to complete checkout', '$.payment_data');
  }
  const provider = paymentData.provider || 'stripe';
  if (provider !== 'stripe') {
    throw new ProtocolFailure('unsupported_provider', `Only provider 'stripe' is supported`, '$.payment_data.provider');
  }
  if (!env.STRIPE_SECRET) {
    throw new ProtocolFailure(
      'payment_not_configured',
      'Merchant has not configured a Stripe payment key; complete is refused (fail-closed)',
      null,
      503,
    );
  }
  const origin = env.STORE_ORIGIN || new URL(request.url).origin;
  const lineItems = [];
  for (const item of session.line_items) {
    lineItems.push([
      `line_items[${lineItems.length}][price_data][currency]=${encodeURIComponent(session.currency)}`,
      `line_items[${lineItems.length}][price_data][unit_amount]=${item.unit_amount}`,
      `line_items[${lineItems.length}][price_data][product_data][name]=${encodeURIComponent(item.name)}`,
      `line_items[${lineItems.length}][quantity]=${item.quantity}`,
    ].join('&'));
  }
  const form = [
    'mode=payment',
    `client_reference_id=${session.id}`,
    `metadata[acp_session_id]=${session.id}`,
    `success_url=${encodeURIComponent(`${origin}/success?session_id={CHECKOUT_SESSION_ID}`)}`,
    `cancel_url=${encodeURIComponent(`${origin}/cancel`)}`,
    ...lineItems,
  ].join('&');

  const stripeRes = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${env.STRIPE_SECRET}`,
      'content-type': 'application/x-www-form-urlencoded',
    },
    body: form,
  });
  const stripeData = await stripeRes.json().catch(() => ({}));
  if (!stripeRes.ok || !stripeData.url) {
    throw new ProtocolFailure('stripe_error', 'Stripe checkout creation failed; order not charged', null, 502);
  }

  session.status = 'completed';
  session.updated_at = nowIso();
  session.continue_url = stripeData.url;
  const order = {
    id: makeId('ord'),
    checkout_session_id: session.id,
    order_number: `${makeId('o').slice(2)}`,
    status: 'created',
    permalink_url: stripeData.url,
    line_items: session.line_items.map((item) => ({
      id: item.id,
      title: item.name,
      product_id: item.product_id,
      quantity: { ordered: item.quantity, current: item.quantity, fulfilled: 0 },
      unit_price: item.unit_amount,
      subtotal: item.unit_amount * item.quantity,
    })),
    totals: session.totals,
    created_at: session.updated_at,
  };
  const submitted = parsed.fulfillment_details || session.fulfillment_details || {};
  const deliverable = submitted.deliverable_sha256;
  if (deliverable !== undefined && deliverable !== null && !/^[a-f0-9]{64}$/i.test(String(deliverable))) {
    throw new ProtocolFailure('deliverable_sha256_invalid', 'deliverable_sha256 must be 64 hex characters', '$.fulfillment_details.deliverable_sha256');
  }
  order.receipt = await signReceipt(env, {
    receipt_version: '1',
    merchant: origin,
    order_id: order.id,
    order_number: order.order_number,
    checkout_session_id: session.id,
    items: session.line_items.map((item) => ({
      product_id: item.product_id,
      quantity: item.quantity,
      unit_amount: item.unit_amount,
    })),
    amount: session.totals.find((t) => t.label === 'total').amount,
    currency: session.currency,
    payment_status: 'pending_hosted_checkout',
    deliverable_sha256: deliverable || null,
    created_at: order.created_at,
  });
  orders.set(order.id, order);
  await putSession('cs', session);
  return json(sessionEnvelope(session, order), 200);
}

async function handleUpdate(request, env, parsed, session) {
  // Update accepts a new line_items set (recomputed from the catalog),
  // buyer info, and fulfillment details. Totals are always recomputed
  // server-side; submitted prices are ignored.
  const currency = parsed.currency || session.currency;
  if (parsed.line_items !== undefined) {
    const cart = buildCart(await catalog(env, request), parsed.line_items, currency);
    session.line_items = cart.lineItems;
    session.totals = cart.totals;
    session.currency = currency;
  }
  if (parsed.buyer !== undefined) session.buyer = parsed.buyer;
  if (parsed.fulfillment_details !== undefined) session.fulfillment_details = parsed.fulfillment_details;
  session.updated_at = nowIso();
  await putSession('cs', session);
  return json(sessionEnvelope(session), 200);
}

async function handleCancel(parsed, session) {
  session.status = 'canceled';
  session.updated_at = nowIso();
  await putSession('cs', session);
  return json(sessionEnvelope(session), 200);
}

async function route(request, env) {
  const url = new URL(request.url);
  const segments = url.pathname.split('/').filter(Boolean);

  // Public receipt surface: a receipt is a proof anyone may check, so these
  // three paths work without a bearer credential and reveal no buyer data.
  if (request.method === 'GET' && url.pathname === '/receipts/key') {
    if (!env.RECEIPT_ED25519_PUBLIC_JWK) return json({ error: 'receipt signing is not configured' }, 404);
    let jwk;
    try {
      jwk = JSON.parse(env.RECEIPT_ED25519_PUBLIC_JWK);
    } catch {
      return json({ error: 'receipt public key is malformed' }, 500);
    }
    return json({ alg: 'Ed25519', key_id: env.RECEIPT_KEY_ID || 'default', jwk }, 200, {
      'cache-control': 'public, max-age=300',
    });
  }
  if (request.method === 'POST' && url.pathname === '/receipts/verify') {
    const body = await readJson(request);
    if (!body || typeof body !== 'object' || !body.receipt) {
      return json({ valid: false, error: 'body must be {"receipt": {...}}' }, 400);
    }
    const valid = await verifyReceipt(env, body.receipt);
    return json({ valid, alg: 'Ed25519' }, valid ? 200 : 422);
  }
  if (request.method === 'GET' && segments.length === 2 && segments[0] === 'receipts') {
    const order = orders.get(segments[1]);
    if (!order || !order.receipt) return json({ error: 'receipt_not_found' }, 404);
    return json(order.receipt, 200);
  }

  if (!bearer(request, env)) {
    return json({ type: 'invalid_request', code: 'unauthorized', message: 'Invalid or missing bearer token' }, 401);
  }
  const headers = requiredPostHeaders(request);
  if (headers.error) return headers.error;

  // GET /checkout_sessions/{id}
  if (request.method === 'GET' && segments.length === 2 && segments[0] === 'checkout_sessions') {
    const session = findSession(segments[1]);
    if (!session) return protocolError('session_not_found', 'Checkout session does not exist', null, 404);
    return json(sessionEnvelope(session));
  }

  if (request.method !== 'POST' || segments.length < 1 || segments[0] !== 'checkout_sessions') {
    return protocolError('not_found', 'Unknown path; try POST /checkout_sessions', null, 404);
  }

  // Idempotency: same key + same body replays the stored result; a different
  // body under the same key is a conflict (409, per the ACP spec).
  const idemKey = request.headers.get('idempotency-key') || '';
  const rawBody = await request.text();
  let parsed;
  try {
    parsed = rawBody ? JSON.parse(rawBody) : {};
  } catch {
    return protocolError('invalid_json', 'Request body must be valid JSON', null, 400);
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return protocolError('invalid_json', 'Request body must be a JSON object', null, 400);
  }

  if (idemKey && idem.has(idemKey)) {
    const prior = idem.get(idemKey);
    if (prior.body !== rawBody) {
      return json({ type: 'invalid_request', code: 'idempotency_conflict', message: 'Idempotency-Key has already been used with a different request body' }, 409);
    }
    return json(prior.result, prior.status, { 'Idempotent-Replayed': 'true' });
  }

  const capture = async (response) => {
    const result = await response.json();
    idem.set(idemKey, { body: rawBody, result, status: response.status });
    return json(result, response.status);
  };

  try {
    // POST /checkout_sessions/{id}/complete
    if (segments.length === 3 && segments[2] === 'complete') {
      const session = findSession(segments[1]);
      if (!session) return protocolError('session_not_found', 'Checkout session does not exist', null, 404);
      return await capture(await handleComplete(request, env, parsed, session));
    }
    // POST /checkout_sessions/{id}/cancel
    if (segments.length === 3 && segments[2] === 'cancel') {
      const session = findSession(segments[1]);
      if (!session) return protocolError('session_not_found', 'Checkout session does not exist', null, 404);
      return await capture(await handleCancel(parsed, session));
    }
    // POST /checkout_sessions/{id}  (update)
    if (segments.length === 2) {
      const session = findSession(segments[1]);
      if (!session) return protocolError('session_not_found', 'Checkout session does not exist', null, 404);
      return await capture(await handleUpdate(request, env, parsed, session));
    }
    // POST /checkout_sessions  (create)
    if (segments.length === 1) {
      return await capture(await createSession(request, env, parsed));
    }
    return protocolError('not_found', 'Unknown path', null, 404);
  } catch (error) {
    if (error instanceof ProtocolFailure) {
      return protocolError(error.code, error.message, error.param, error.status);
    }
    throw error;
  }
}

export default {
  async fetch(request, env) {
    try {
      return await route(request, env);
    } catch (error) {
      return json({ type: 'processing_error', code: 'internal_error', message: 'Unexpected server failure' }, 500);
    }
  },
};
"""

WORKER_TEST_MJS = r"""// Self-test for the generated ACP store endpoint.
// Run with: node --test checkout_sessions.test.mjs
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import test from 'node:test';
import worker from './checkout_sessions.js';

const PRODUCTS = {
  products: [
    { id: 'starter', name: 'Starter pack', unit_amount: 1000, currency: 'usd', max_quantity: 10, availability_status: 'in_stock' },
    { id: 'premium', name: 'Premium pack', unit_amount: 2500, currency: 'usd', max_quantity: 3, availability_status: 'in_stock' },
  ],
};

const baseEnv = {
  PRODUCTS_JSON: JSON.stringify(PRODUCTS),
  STORE_ORIGIN: 'https://store.example',
  STRIPE_SECRET: 'sk_test_dummy',
};

function request(path, { method = 'POST', body, headers = {} } = {}) {
  return new Request(`https://store.example${path}`, {
    method,
    headers: {
      'content-type': 'application/json',
      'Idempotency-Key': `it-${crypto.randomUUID()}`,
      'API-Version': '2026-04-17',
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function stubStripe(handler) {
  const original = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input.url;
    if (url.startsWith('https://api.stripe.com/')) return handler(input, init);
    return original(input, init);
  };
  return () => { globalThis.fetch = original; };
}

test('creates a session with authoritative totals and fills the ACP required fields', async () => {
  const restore = stubStripe(async () => Response.json({ id: 'cs_test_1', url: 'https://checkout.stripe.com/pay/1' }));
  try {
    const res = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 2 }], currency: 'usd' } }), baseEnv);
    assert.equal(res.status, 201);
    const session = await res.json();
    assert.match(session.id, /^cs_/);
    assert.equal(session.status, 'ready_for_payment');
    assert.equal(session.currency, 'usd');
    assert.equal(session.line_items.length, 1);
    assert.equal(session.line_items[0].unit_amount, 1000);
    assert.equal(session.totals.find((t) => t.label === 'total').amount, 2000);
    assert.ok(Array.isArray(session.fulfillment_options));
    assert.ok(Array.isArray(session.messages) && Array.isArray(session.links));
    assert.ok(session.capabilities.payment.handlers[0].psp === 'stripe');
  } finally {
    restore();
  }
});

test('rejects missing Idempotency-Key on POST', async () => {
  const res = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' }, headers: { 'Idempotency-Key': '' } }), baseEnv);
  assert.equal(res.status, 400);
  const error = await res.json();
  assert.equal(error.code, 'idempotency_key_required');
});

test('rejects unknown products and oversize quantity (fail-closed pricing)', async () => {
  const unknown = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'nope', quantity: 1 }], currency: 'usd' } }), baseEnv);
  assert.equal(unknown.status, 422);
  assert.equal((await unknown.json()).code, 'product_not_found');
  const oversize = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'premium', quantity: 99 }], currency: 'usd' } }), baseEnv);
  assert.equal(oversize.status, 422);
  assert.equal((await oversize.json()).code, 'quantity_invalid');
});

test('retrieves and updates a session, and 404s for unknown ids', async () => {
  const create = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' } }), baseEnv);
  const session = await create.json();
  const get = await worker.fetch(new Request(`https://store.example/checkout_sessions/${session.id}`, { method: 'GET' }), baseEnv);
  assert.equal(get.status, 200);
  assert.equal((await get.json()).id, session.id);
  const missing = await worker.fetch(new Request('https://store.example/checkout_sessions/cs_does_not_exist', { method: 'GET' }), baseEnv);
  assert.equal(missing.status, 404);
  assert.equal((await missing.json()).code, 'session_not_found');
});

test('completes with a Stripe hosted checkout URL and an order', async () => {
  const restore = stubStripe(async () => Response.json({ id: 'cs_test_1', url: 'https://checkout.stripe.com/pay/1' }));
  try {
    const create = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' } }), baseEnv);
    const session = await create.json();
    const complete = await worker.fetch(request(`/checkout_sessions/${session.id}/complete`, {
      body: { buyer: { email: 'buyer@example.com' }, payment_data: { token: 'hosted_checkout', provider: 'stripe' } },
    }), baseEnv);
    assert.equal(complete.status, 200);
    const result = await complete.json();
    assert.equal(result.status, 'completed');
    assert.ok(result.order);
    assert.equal(result.order.status, 'created');
    assert.match(result.order.id, /^ord_/);
    assert.equal(result.continue_url, 'https://checkout.stripe.com/pay/1');
  } finally {
    restore();
  }
});

test('refuses completion when no Stripe key is configured (fail-closed)', async () => {
  const create = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' } }), { ...baseEnv, STRIPE_SECRET: undefined });
  const session = await create.json();
  const complete = await worker.fetch(request(`/checkout_sessions/${session.id}/complete`, {
    body: { payment_data: { token: 'hosted_checkout', provider: 'stripe' } },
  }), { ...baseEnv, STRIPE_SECRET: undefined });
  assert.equal(complete.status, 503);
  const error = await complete.json();
  assert.equal(error.code, 'payment_not_configured');
});

test('requires a valid bearer token when AGENT_API_KEY is configured', async () => {
  const env = { ...baseEnv, AGENT_API_KEY: 'secret-one' };
  const denied = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' } }), env);
  assert.equal(denied.status, 401);
  const allowed = await worker.fetch(request('/checkout_sessions', {
    body: { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' },
    headers: { Authorization: 'Bearer secret-one' },
  }), env);
  assert.equal(allowed.status, 201);
});

test('replays the same idempotency key and rejects conflicting bodies', async () => {
  const key = 'it-replay-key';
  const body = { line_items: [{ id: 'starter', quantity: 1 }], currency: 'usd' };
  const first = await worker.fetch(request('/checkout_sessions', { body, headers: { 'Idempotency-Key': key } }), baseEnv);
  assert.equal(first.status, 201);
  const replay = await worker.fetch(request('/checkout_sessions', { body, headers: { 'Idempotency-Key': key } }), baseEnv);
  assert.equal(replay.status, 201);
  assert.equal((await replay.json()).id, (await first.json()).id);
  const conflict = await worker.fetch(request('/checkout_sessions', { body: { line_items: [{ id: 'premium', quantity: 1 }], currency: 'usd' }, headers: { 'Idempotency-Key': key } }), baseEnv);
  assert.equal(conflict.status, 409);
  assert.equal((await conflict.json()).code, 'idempotency_conflict');
});
// --- signed receipts ---------------------------------------------------------

function receiptEnv() {
  const { publicKey, privateKey } = generateKeyPairSync('ed25519');
  return {
    ...baseEnv,
    RECEIPT_ED25519_PRIVATE_KEY: privateKey.export({ format: 'der', type: 'pkcs8' }).toString('base64'),
    RECEIPT_ED25519_PUBLIC_JWK: JSON.stringify(publicKey.export({ format: 'jwk' })),
  };
}

function canon(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return '[' + value.map(canon).join(',') + ']';
  const keys = Object.keys(value).filter((k) => value[k] !== undefined).sort();
  return '{' + keys.map((k) => JSON.stringify(k) + ':' + canon(value[k])).join(',') + '}';
}

function b64uToBytes(value) {
  return new Uint8Array(Buffer.from(value.replace(/-/g, '+').replace(/_/g, '/'), 'base64'));
}

async function completeOnce(env, extra = {}) {
  const restore = stubStripe(async () => Response.json({ id: 'cs_test_1', url: 'https://checkout.stripe.com/pay/1' }));
  // Receipt checks run with a bearer key configured too, so prove the public
  // receipt paths work without one while the storefront itself stays locked.
  const headers = env.AGENT_API_KEY ? { Authorization: `Bearer ${env.AGENT_API_KEY}` } : {};
  try {
    const create = await worker.fetch(request('/checkout_sessions', {
      body: { line_items: [{ id: 'starter', quantity: 2 }], currency: 'usd' },
      headers,
    }), env);
    const session = await create.json();
    const complete = await worker.fetch(request(`/checkout_sessions/${session.id}/complete`, {
      body: { buyer: { email: 'buyer@example.com' }, payment_data: { token: 'hosted_checkout', provider: 'stripe' }, ...extra },
      headers,
    }), env);
    return { session, complete, result: await complete.json() };
  } finally {
    restore();
  }
}

test('completion emits an Ed25519 receipt any agent can verify offline', async () => {
  const env = receiptEnv();
  const { result } = await completeOnce(env);
  assert.equal(result.order.receipt.alg, 'Ed25519');
  const payload = result.order.receipt.payload;
  assert.equal(payload.order_id, result.order.id);
  assert.equal(payload.amount, 2000);
  assert.equal(payload.currency, 'usd');
  assert.equal(payload.items[0].product_id, 'starter');
  assert.equal(payload.items[0].quantity, 2);
  assert.equal(payload.payment_status, 'pending_hosted_checkout');
  assert.equal(payload.deliverable_sha256, null);

  const publicKey = await crypto.subtle.importKey('jwk', JSON.parse(env.RECEIPT_ED25519_PUBLIC_JWK), { name: 'Ed25519' }, false, ['verify']);
  const ok = await crypto.subtle.verify(
    { name: 'Ed25519' },
    publicKey,
    b64uToBytes(result.order.receipt.signature),
    new TextEncoder().encode(canon(payload)),
  );
  assert.equal(ok, true);
});

test('tampering with the payload invalidates the receipt', async () => {
  const env = receiptEnv();
  const { result } = await completeOnce(env);
  const tampered = JSON.parse(JSON.stringify(result.order.receipt));
  tampered.payload.amount = 1;
  const res = await worker.fetch(new Request('https://store.example/receipts/verify', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ receipt: tampered }),
  }), env);
  assert.equal(res.status, 422);
  assert.equal((await res.json()).valid, false);
});

test('a valid receipt verifies over the public endpoint and is refetchable by order id', async () => {
  const env = { ...receiptEnv(), AGENT_API_KEY: 'secret-one' };
  const { result } = await completeOnce(env);
  const verify = await worker.fetch(new Request('https://store.example/receipts/verify', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ receipt: result.order.receipt }),
  }), env);
  assert.equal(verify.status, 200);
  assert.equal((await verify.json()).valid, true);

  const fetchReceipt = await worker.fetch(new Request(`https://store.example/receipts/${result.order.id}`, { method: 'GET' }), env);
  assert.equal(fetchReceipt.status, 200);
  assert.equal((await fetchReceipt.json()).signature, result.order.receipt.signature);

  const key = await worker.fetch(new Request('https://store.example/receipts/key', { method: 'GET' }), env);
  assert.equal(key.status, 200);
  assert.equal((await key.json()).alg, 'Ed25519');
});

test('no receipt is fabricated when signing is not configured', async () => {
  const { result } = await completeOnce(baseEnv);
  assert.equal(result.order.receipt, null);
  const key = await worker.fetch(new Request('https://store.example/receipts/key', { method: 'GET' }), baseEnv);
  assert.equal(key.status, 404);
});

test('a delivered artifact is bound into the receipt, and a bad hash is refused', async () => {
  const env = receiptEnv();
  const sha = 'a'.repeat(64);
  const { result } = await completeOnce(env, { fulfillment_details: { deliverable_sha256: sha } });
  assert.equal(result.order.receipt.payload.deliverable_sha256, sha);

  const bad = await completeOnce(env, { fulfillment_details: { deliverable_sha256: 'not-a-hash' } });
  assert.equal(bad.complete.status, 422);
  assert.equal(bad.result.code, 'deliverable_sha256_invalid');
});

"""

# Files the scaffolder writes, in write order. "unused" flag is for lint.
GENERATED_FILES: list[tuple[str, str]] = [
    ("README.md", README),
    ("products.json", json.dumps(PRODUCTS_JSON, indent=2) + "\n"),
    ("for-agents.md", FOR_AGENTS_MD),
    ("wrangler.toml.example", WRANGLER_TOML),
    ("package.json", json.dumps(PACKAGE_JSON, indent=2) + "\n"),
    ("checkout_sessions.js", WORKER_JS),
    ("checkout_sessions.test.mjs", WORKER_TEST_MJS),
]


def _banner() -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "Store scaffold ready. Next: edit products.json, set your secrets, "
        f"and deploy (see README.md). Generated {generated_at}."
    )


def cmd_new(args: argparse.Namespace) -> int:
    target = Path(args.directory)
    if target.exists() and any(target.iterdir()):
        print(f"refusing: {target} exists and is not empty", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)
    for filename, content in GENERATED_FILES:
        (target / filename).write_text(content, encoding="utf-8")
    example_key = secrets.token_urlsafe(24)
    print(f"wrote {len(GENERATED_FILES)} files to {target}")
    print(_banner())
    print(f"example AGENT_API_KEY: {example_key}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sell_to_agents.py",
        description="One-command 'sell to agents' template: generate an ACP-compatible "
                    "merchant endpoint for a Hermes-built store.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="scaffold a new store directory")
    new.add_argument("directory", help="target directory, e.g. ./my-store")
    new.set_defaults(func=cmd_new)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())