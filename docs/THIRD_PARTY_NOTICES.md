# Licensing and provenance

## Project code

This candidate contains newly written generic implementations of reviewed local
CSV-validation, missing-value reporting, weekly comparison and experiment-ledger
behaviors. No source-repository history, production data, branding, policy files,
private strategy documents or verbatim private source modules were imported.
Source files with missing/uncertain redistribution rights were excluded as files.

The proposed MIT license applies to original project code whose rights the
maintainer controls. Public release still requires the owner's confirmation of
those rights and the publication manifest. A copyright license does not establish
rights in somebody else's code or trademarks. The project name's registry and
trademark availability has not been certified.

## Dependencies and tooling

| Component | Use | License / source | Distributed here? |
|---|---|---|---|
| Python standard library | Runtime | PSF, https://docs.python.org/3/license.html | No; users install Python separately |
| setuptools 84.0.0 | Pinned build backend | MIT, https://github.com/pypa/setuptools/blob/main/LICENSE | No source or binaries bundled |
| unittest | Test runner in Python stdlib | Python license above | No |
| actions/checkout | CI checkout | MIT, https://github.com/actions/checkout/blob/main/LICENSE | No; referenced by commit |
| actions/setup-python | CI interpreter setup | MIT, https://github.com/actions/setup-python/blob/main/LICENSE | No; referenced by commit |

No vendored third-party code is present. Original runtime has no pip dependencies.
Python and build tools retain their own license texts in their installations.
If future packaging bundles third-party code or a Python runtime, their notices
must be included at that point; do not assume this table replaces those obligations.

MIT reference: https://opensource.org/license/mit.
