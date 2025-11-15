# nhomltmck

## HTTP/HTTPS Server

- Install deps:

```powershell
pip install -r requirements.txt
```

- Run HTTP server:

```powershell
python -m server.http_server
- Combined TCP + HTTP demo (single process):

```powershell
# Optional DB integration
$env:ENABLE_DB = "true"
python -m server.run_combined
```

Then test:
- TCP uploads via existing desktop client (port 9999)
- HTTP uploads via `POST /api/upload` (port 8000)
- Check unified status: `GET http://127.0.0.1:8000/api/health` (includes TCP stats)

```

- Configure HTTPS (optional):
	- Provide cert/key files and set env vars, then run:

```powershell
$env:ENABLE_HTTPS = "true"
$env:SSL_CERTFILE = "C:\path\to\cert.pem"
$env:SSL_KEYFILE = "C:\path\to\key.pem"
python -m server.http_server
```

- Endpoints:
	- `GET /api/health`
	- `POST /api/register` { username, password }
	- `POST /api/login` { username, password }
	- `POST /api/upload` multipart form: `file`, `user_id` (int, optional; default guest=0)
	- `GET /api/files?user_id=...`
	- `GET /api/stats`

Note: When DB is disabled (`ENABLE_DB=false`), uploads still stream and succeed but only as metadata-less operations (no DB records).

## HTTP Demo Client

- Install deps:
```powershell
pip install -r requirements.txt
```

- Quick usage:
```powershell
# Health
python -m client.http_client health

# Register & login
python -m client.http_client register --username demo --password secret
python -m client.http_client login --username demo --password secret

# Upload as guest
python -m client.http_client upload --file README.md --user-id 0

# List files & stats
python -m client.http_client files --user-id 0
python -m client.http_client stats

# Custom server URL
$env:HTTP_SERVER_URL = "http://127.0.0.1:8000"; python -m client.http_client health
```