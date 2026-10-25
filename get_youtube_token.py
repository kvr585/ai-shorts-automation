import os
import json
import urllib.parse
import urllib.request
import http.server
import socketserver

CLIENT_ID = "53102647410-rmlfl4q59p7vthc64fieufmh8vqdic2d.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8080/"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main():
    print("=" * 60)
    print("🔑 ONE-TIME YOUTUBE REFRESH TOKEN GENERATOR")
    print("=" * 60)
    print("\nNote: Make sure 'http://localhost:8080/' is added to")
    print("Authorized redirect URIs in Google Cloud Console:")
    print("https://console.cloud.google.com/apis/credentials\n")

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent"
        })
    )

    print("Step 1: Open this URL in your browser to authorize:")
    print("-" * 60)
    print(auth_url)
    print("-" * 60)

    auth_code = ""

    class OAuthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorization Successful!</h1><p>You can close this tab and return to the terminal.</p>")
            else:
                self.send_response(400)
                self.end_headers()

    print("\nStep 2: Waiting for authorization on http://localhost:8080/ ...")
    try:
        with socketserver.TCPServer(("localhost", 8080), OAuthHandler) as httpd:
            httpd.handle_request()
    except Exception as e:
        print("Local server error, manual code entry fallback:", e)
        auth_code = input("Or paste the 'code' parameter from the URL here: ").strip()

    if not auth_code:
        print("No authorization code received.")
        return

    print("\nStep 3: Exchanging authorization code for permanent refresh token...")
    token_url = "https://oauth2.googleapis.com/token"
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }).encode("utf-8")

    req = urllib.request.Request(token_url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read().decode("utf-8"))

    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        print("\n🎉 SUCCESS! YouTube Refresh Token obtained:")
        print(f"REFRESH_TOKEN: {refresh_token}")

        token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_token.json")
        with open(token_file, "w") as f:
            json.dump({
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token
            }, f, indent=2)
        print(f"Saved to: {token_file}")
    else:
        print("Response received, but no refresh_token was returned (tokens might already be consented):", tokens)


if __name__ == "__main__":
    main()
