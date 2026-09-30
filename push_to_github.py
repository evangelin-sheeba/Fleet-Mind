"""
Git Push Utility for Fleet-Mind using pure-Python dulwich.
Pushes the entire local repository (3-layer stack, Streamlit, FastAPI, JSON DB, tests, models)
to https://github.com/evangelin-sheeba/Fleet-Mind.git using GitHub Personal Access Token.
"""

import sys
import os
from dulwich.repo import Repo
from dulwich import porcelain

def main():
    repo_path = os.path.dirname(os.path.abspath(__file__))
    remote_base = "github.com/evangelin-sheeba/Fleet-Mind.git"

    print("=" * 70)
    print("  ANTI-GRAVITY // PUSH FLEET-MIND TO GITHUB REPOSITORY")
    print("  Target: https://github.com/evangelin-sheeba/Fleet-Mind.git")
    print("=" * 70)
    print()

    # Get token from CLI arg or prompt
    token = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        token = sys.argv[1].strip()
    else:
        print("GitHub requires a Personal Access Token (PAT) with 'repo' scope to push.")
        print("If you do not have one yet:")
        print("  1. Open: https://github.com/settings/tokens")
        print("  2. Click 'Generate new token (classic)'")
        print("  3. Check the 'repo' permission box and click 'Generate token'")
        print()
        try:
            token = input("Enter your GitHub Personal Access Token (ghp_...): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(1)

    if not token:
        print("\n[!] Error: No token provided. Push aborted.")
        sys.exit(1)

    auth_url = f"https://evangelin-sheeba:{token}@{remote_base}"

    print("\n[*] Packaging repository commits and connecting to GitHub...")
    try:
        repo = Repo(repo_path)
        # Add any uncommitted files
        porcelain.add(repo_path)
        try:
            porcelain.commit(
                repo_path,
                message=b"Update: FleetMind 3-Layer Architecture & Distributed 2-Laptop System",
                committer=b"Evangelin Sheeba <evangelin.sheeba@example.com>",
                author=b"Evangelin Sheeba <evangelin.sheeba@example.com>"
            )
        except Exception:
            pass  # No new changes to commit

        # Push to main branch on GitHub
        print("[*] Uploading code to branch 'main'...")
        porcelain.push(repo, auth_url, "refs/heads/main:refs/heads/main", force=True)
        print()
        print("=" * 70)
        print("  [SUCCESS] All Fleet-Mind code has been pushed to GitHub!")
        print("  View repository: https://github.com/evangelin-sheeba/Fleet-Mind")
        print("=" * 70)
        print()
    except Exception as e:
        error_msg = str(e)
        if "HTTPUnauthorized" in str(type(e)) or "401" in error_msg:
            print("\n[X] Authentication Failed: The token was rejected by GitHub.")
            print("    Please ensure the token has the 'repo' scope permission.")
        else:
            print(f"\n[X] Push Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
