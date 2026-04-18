# Cache Proxy SPEC

## Purpose
A cache proxy server placed between Nginx and Origin(S3), supporting LRU, LFU, and TTL.

## Request Flow
Client -> Nginx -> Cache Proxy -> Origin

## Cache Key
Default cache key:
METHOD:path?query

Examples:
- GET:/small.txt
- GET:/image.png?version=1

## Policies
- LRU: evict least recently accessed object
- LFU: evict least frequently accessed object; tie-break by oldest last_access
- TTL: object expires after configured TTL seconds

## Capacity
- Cache limit is measured in bytes
- Before insert, evict objects until enough capacity exists
- If object size > max_bytes, skip caching and mark reason as `oversize`

## Response Headers
- X-Cache: HIT | MISS
- X-Cache-Policy: LRU | LFU | TTL
- X-Cache-Key: computed cache key
- X-Cache-Reason: fresh | not_found | expired | stored | oversize

## Admin Endpoints
- GET /health
- GET /cache/stats
- GET /cache/entries
