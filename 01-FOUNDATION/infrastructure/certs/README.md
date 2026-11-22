# TLS certificates for the production reverse proxy

Place your wildcard certificate here before starting the production stack:

- `fullchain.pem` — certificate plus intermediate chain
- `privkey.pem` — private key (never commit it)

The files are mounted read-only into nginx at `/etc/nginx/certs/`. For
`*.azadexa.com` multi-tenant subdomains use a wildcard certificate (DNS-01
challenge). Local development can generate a self-signed pair with:

```powershell
openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
  -keyout privkey.pem -out fullchain.pem -subj "/CN=*.azadexa.com"
```

The repository ignores `*.pem` so real keys cannot be committed by accident.
