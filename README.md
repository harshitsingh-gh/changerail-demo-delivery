# changerail-demo-delivery

Synthetic delivery estimate service — pipeline P2 example application for
the ChangeRail POC (spec SS3).

- **Repository identity:** `changerail-demo-delivery`
- **Test profile:** `pytest_unit_delivery`
- **Public contract:** `POST /estimate` —
  `{"weight_kg":"1.250","destination":"US","shipment_id":"00017"}` →
  `{"shipment_id":"00017","services":[{"id":...,"charge_minor":N,"delivery_at":"...Z"}]}`;
  services sorted by charge then id; empty availability returns an empty
  list; exhausted upstream timeouts return 503
  `{"error":"upstream_timeout"}`. Test timestamps are fixed fixture data.
- **Health endpoint:** `GET /ready`

## Layout

```
delivery_app/       application package (app.py implements POST /estimate)
tests/              ordinary in-repo pytest suite (test profile pytest_unit_delivery)
conftest.py         local path shim only (see below)
```

The application depends on the small owned dependency `fixture_client`
(v1/1.0.0 API: kilograms weight argument, integer shipment identifier,
naive UTC datetimes, plain service list, `[]` empty availability,
`UpstreamTimeout`). In a deployed candidate repository this dependency
arrives as a hash-pinned wheel; in this build workspace the `conftest.py`
shim points at `fixtures/dependency_versions/old` so the tests run without
an install step.

Run the suite from the repository root:

```
.venv/bin/python -m pytest examples/delivery/tests -q
```
