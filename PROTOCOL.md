# Urja Meter Ops protocol notes

This document captures the protocol findings that were verified against the live legacy portal at https://urja-ops.flockenergy.tech.

## Verified portal behaviour

### Login flow

- Login page: GET https://urja-ops.flockenergy.tech/login
- Form fields: `email` and `password`
- HTTP method: POST to /login
- Success behaviour: the login request returns a 200 response body containing a JSON-style redirect payload and a session cookie named `__Secure-better-auth.session_token`.
- Redirect target: `/meters`
- Cookies: a session cookie is set with `HttpOnly`, `Secure`, and `SameSite=Lax` and shares a 3600-second lifetime.
- CSRF: no explicit CSRF field was present in the HTML; the site blocks direct cross-site POSTs with a 403 when the login is submitted without the expected same-origin headers.

### Authentication method

The working request shape used for successful authentication was:

- `Origin: https://urja-ops.flockenergy.tech`
- `Referer: https://urja-ops.flockenergy.tech/login`
- `Content-Type: application/x-www-form-urlencoded`
- `POST https://urja-ops.flockenergy.tech/login` with `email` and `password`

When the credentials are valid, the portal responds with a redirect-style payload and a `Set-Cookie` header. This is sufficient to establish a valid browser session.

### Meter list endpoint

- URL: https://urja-ops.flockenergy.tech/portal/meters/search
- Method: GET
- Query parameters:
  - `q`: free-text search
  - `page`: 1-based page index
- Response: JSON with top-level `data` and `total` keys.

Example response:

```json
{
  "data": [
    {
      "meterId": "J100000",
      "serialNo": "SE33962",
      "make": "HPL",
      "phaseType": "single",
      "installStatus": "Decommissioned",
      "dtCode": "DT-001"
    }
  ],
  "total": 403
}
```

### Meter detail page

The visible UI route is:

- GET https://urja-ops.flockenergy.tech/meters/{meter_id}

The page returns a server-rendered HTML page containing a script payload with the embedded fields:

- `meterId`
- `detail.data[]` with entries like `parameterName` and `parameterValue`
- `hierarchy` with a dictionary such as `Zone`, `Circle`, `Division`, `Subdivision`, `Sub Station`, `Feeder`, and `DT`

The geometry endpoints used by the frontend were also observed to be:

- GET /portal/meters/{meter_id}/geo
- GET /portal/meters/{meter_id}/energy

### Geo endpoint

- URL: https://urja-ops.flockenergy.tech/portal/meters/{meter_id}/geo
- Response:

```json
{
  "data": {
    "latitude": "26.938961002479868",
    "longitude": "75.83095696146852"
  }
}
```

### Energy endpoint

- URL: https://urja-ops.flockenergy.tech/portal/meters/{meter_id}/energy
- Response: JSON array under `data`, each item containing values such as:
  - `timestamp`: `dd/mm/YYYY HH:MM`
  - `kwh`
  - `kvah`
  - `voltR`

Example:

```json
{
  "data": [
    {
      "timestamp": "23/06/2026 23:30",
      "kwh": "48438.74",
      "kvah": "52313.84",
      "voltR": "226"
    }
  ]
}
```

### Observed data semantics

- `phaseType` values observed: `single`, `three`
- `installStatus` values observed: `Installed`, `Faulty`, `Decommissioned`
- `meterId` values follow the pattern `J100000`, `J100001`, ...
- The list page renders a `0 total` message when no meter matches, and otherwise shows a paginated table with 20 results per page.

### Session lifetime and expiry

- Session cookie lifetime is set to 3600 seconds (`Max-Age=3600`).
- Expired sessions were not directly observed in this environment, but the frontend clearly re-authenticates via a login page if the cookie is absent or invalid.
- The adapter treats `401`, `403`, or a redirect to `/login` as an expired-session condition.

### Error handling observed

- Cross-site POST without valid same-origin headers returns 403 with the message `Cross-site POST form submissions are forbidden`.
- Invalid credentials are treated as a failed login attempt rather than a raw server error.
- The application uses a login page and a session cookie; this is not a bearer-token API.

## Remaining unverified points

- Not verified: whether a public API exists for transformer hierarchy beyond the UI data embedded in the page model.
- Not verified: whether there are additional query filters beyond the `q` and `page` parameters used on the search page.
- Not verified: whether the portal supports bulk exports or other writes beyond the authenticated read-only navigation inspected here.
- Not verified: whether the energy endpoint accepts date-range filters; no such filter was observed in the frontend or in the inspected client code.

## Assessment

The portal exposes a browser-authenticated JSON API for listing meters and reading energy data. The adapter implements safe, read-only wrappers around those endpoints while treating the HTML page as the source for detailed meter metadata and hierarchy context.
