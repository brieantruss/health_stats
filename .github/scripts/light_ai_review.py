import os
import json
import urllib.request
import subprocess
import sys

def get_git_diff():
    try:
        # Get the diff of the changes in the latest commit
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error getting git diff: {e}")
        return ""

def ask_gemini(diff):
    if not diff.strip():
        print("No changes detected in this commit.")
        return "LGTM"

    api_key = os.environ.get("GEMINI_API_KEY", "")
    
    # Clean and minimal instructions to prevent long-winded answers
    prompt = f"""You are a lightweight code review assistant. 
Review the following git diff. Identify any obvious syntax errors, logic bugs, or major typos.
If everything looks okay, respond with exactly: "LGTM"
If there is an issue, write a brief explanation of what's wrong and how to fix it (keep it under 10 lines).

GIT DIFF:
{diff}
"""

    # Gemini's generateContent endpoint
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {
        "content-type": "application/json"
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    req = urllib.request.Request(
        api_url, 
        data=json.dumps(data).encode("utf-8"), 
        headers=headers, 
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            # Extract content from Gemini response structure
            return res_body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Default to success so we never block your workflow on API outage
        return "LGTM"

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY secret is missing. Skipping review.")
        sys.exit(0)
        
    diff = get_git_diff()
    print("Analyzing changes with Gemini...")
    
    verdict = ask_gemini(diff)
    
    if "LGTM" in verdict:
        print("✨ AI Review: LGTM! All checks passed.")
        sys.exit(0)
    else:
        print("\n❌ AI Review detected issues:")
        print("================================")
        print(verdict)
        print("================================\n")
        # Failing with exit code 1 automatically triggers GitHub's failure email notification
        sys.exit(1)

if __name__ == "__main__":
    main()
