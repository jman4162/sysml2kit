# Security policy

## Supported versions

Only the latest release line receives fixes.

## Reporting

Report vulnerabilities privately via GitHub Security Advisories
(https://github.com/jman4162/sysml2kit/security/advisories/new) or email
jhodge007@gmail.com. Expect an acknowledgment within a week.

## Notes for deployers

- `sysml2kit.api.SysMLApiClient` sends the bearer token you give it to the
  base URL you give it, over whatever scheme that URL uses. Use HTTPS.
- Model files are data, not code: the JSON and `.sysml` readers do not
  execute model content. The optional sysmlpy backend parses untrusted text
  with an ANTLR-generated parser; treat very large inputs as a
  denial-of-service surface and bound file sizes upstream if you accept
  models from strangers.
