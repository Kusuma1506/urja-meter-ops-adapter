### What assumptions did you make?

I assumed that the legacy portal would behave as a read-only browser app with a signed-in session cookie, because the live page clearly uses a standard login form and the authenticated frontend calls JSON endpoints under `/portal/...`. I also assumed that endpoint behavior would remain stable across the session lifetime, which is consistent with the way the frontend issues requests after login. For missing or malformed fields, I treated the portal as authoritative and only normalized values when the underlying response clearly had a well-defined data type, such as strings that represented numeric readings or ISO-like timestamps.

### Which part was most difficult, and how did you get unstuck?

The toughest part was discovering the real authentication and data-loading workflow without inventing endpoints or claiming success prematurely. The direct POST to `/login` initially failed with a 403 due to cross-site form protection, which forced a more precise investigation: I checked the live login page, added same-origin headers, and then validated the resulting session cookie and authenticated JSON calls. Once that flow was confirmed, the rest of the adapter was straightforward: list/search endpoints, geo endpoints, and the HTML-embedded meter detail payload.

### If you had another day, what would you improve?

I would add stronger integration tests that exercise real upstream payload fixtures end-to-end, a small caching layer with explicit freshness rules for meter lists and consumption snapshots, and observability around login retries, session expiry, and rate limiting. I would also investigate whether a more structured backend route exists for detailed meter metadata beyond the HTML payload that the UI embeds into the page.

### What mistake did you make while solving this?

The most important mistake was to assume the login form was a simple submit without checking the browser requirements. The direct POST initially returned a 403, which taught me to respect the portal’s same-origin and CSRF behavior before claiming the API contract was valid. That issue was resolved by reproducing the actual browser headers and cookie flow rather than guessing a different payload.

### If you were reviewing your own submission, what would you criticise?

The main limitation is that this adapter depends on a browser-authenticated session model and on front-end-derived detail fields embedded in HTML, both of which are a little less stable than a first-class API. The code is intentionally conservative and read-only, but it is still a wrapper around a UI portal rather than a fully owned integration contract. The tests are meaningful and mocked, but they cannot replace production verification against the live portal if that environment changes.
