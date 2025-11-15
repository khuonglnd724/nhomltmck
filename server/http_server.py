import os
import ssl
import uvicorn


def run():
    host = os.getenv("HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("HTTP_PORT", "8000"))
    enable_https = os.getenv("ENABLE_HTTPS", "false").lower() in ("1", "true", "yes")
    certfile = os.getenv("SSL_CERTFILE")
    keyfile = os.getenv("SSL_KEYFILE")

    ssl_kw = {}
    if enable_https and certfile and keyfile:
        ssl_kw = {"ssl_keyfile": keyfile, "ssl_certfile": certfile}

    uvicorn.run(
        "server.http_app:app",
        host=host,
        port=port,
        reload=False,
        **ssl_kw,
    )


if __name__ == "__main__":
    run()
