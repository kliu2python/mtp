# SSL Certificates

This directory contains SSL/TLS certificates for HTTPS support.

## Required Files

Place the following files in this directory:

- `server.crt` - SSL certificate file for mtp.qa.fortinet-us.com
- `server.key` - Private key file for the certificate

## Certificate Requirements

- The certificate should be valid for the domain: `mtp.qa.fortinet-us.com`
- The certificate should be in PEM format
- The private key should be unencrypted or you'll need to update the nginx configuration

## Generating Self-Signed Certificates (Testing Only)

For testing purposes, you can generate self-signed certificates:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key \
  -out server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=mtp.qa.fortinet-us.com"
```

**Note**: Self-signed certificates will show security warnings in browsers. For production, use certificates from a trusted CA.

## Security

- Keep `server.key` secure and never commit it to version control
- The `.gitignore` file should exclude `*.key` and `*.crt` files
- Ensure proper file permissions (600 for .key, 644 for .crt)
