import os
import sys
import json
import requests
from github import Github
from google import genai

def run_repair_engine():
    print("🤖 INDUSTRIAL ENGINE: Initiating Autonomous Code Repair Protocol...")

    gemini_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("REPO_NAME")
    run_id = os.getenv("RUN_ID")

    if not gemini_key or not github_token or not repo_name:
        print("❌ CRITICAL ERROR: Missing required secret parameters.")
        sys.exit(1)

    gh = Github(github_token)
    repo = gh.get_repo(repo_name)

    print(f"📊 Fetching workflow failure logs for Run ID: {run_id}...")
    failure_log = "Error: Test suite execution failed with non-zero exit status."
    
    try:
        run = repo.get_workflow_run(int(run_id))
        logs_url = run.logs_url
        headers = {"Authorization": f"token {github_token}"}
        response = requests.get(logs_url, headers=headers, timeout=30)
        if response.status_code == 200:
            failure_log = response.text[-3000:]
    except Exception as e:
        print(f"⚠️ Warning: Could not download full log zip: {e}")

    target_file = None
    target_content = ""
    
    for root, _, files in os.walk("."):
        if ".git" in root or "scripts" in root or ".github" in root:
            continue
        for file in files:
            if file.endswith((".py", ".js", ".ts")):
                target_file = os.path.join(root, file)
                with open(target_file, "r", encoding="utf-8") as f:
                    target_content = f.read()
                break
        if target_file:
            break

    if not target_file:
        print("❌ CRITICAL ERROR: No eligible source code files located for analysis.")
        sys.exit(1)

    print(f"🔍 Target file identified: {target_file}")
    print("⚡ Transmitting failure payload to Gemini AI Engine...")
    
    client = genai.Client(api_key=gemini_key)
    system_prompt = (
        "You are an expert autonomous software engineer. Your job is to fix broken source code based on error logs.\n"
        "RULES:\n"
        "1. Return ONLY the fully corrected executable file content.\n"
        "2. Do NOT use markdown code blocks like ```python or ``` javascript in your output.\n"
        "3. Do NOT include explanations, introduction, or text outside the raw code."
    )
    user_prompt = f"TARGET FILE: {target_file}\n\nCURRENT SOURCE CODE:\n{target_content}\n\nFAILURE LOGS:\n{failure_log}\n\nPROVIDE REPAIRED CODE:"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={"system_instruction": system_prompt}
        )
        repaired_code = response.text.strip()
        if repaired_code.startswith("```"):
            lines = repaired_code.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            repaired_code = "\n".join(lines).strip()
    except Exception as e:
        print(f"❌ CRITICAL ERROR during Gemini synthesis: {e}")
        sys.exit(1)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(repaired_code)

    branch_name = f"autodev-patch-{run_id}"
    base_branch = repo.default_branch

    main_ref = repo.get_git_ref(f"heads/{base_branch}")
    main_sha = main_ref.object.sha

    try:
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_sha)
    except Exception as e:
        print(f"⚠️ Branch reference notice: {e}")

    file_contents = repo.get_contents(target_file, ref=branch_name)
    repo.update_file(
        path=target_file,
        message=f"fix(autodev): autonomous repair patch for run #{run_id}",
        content=repaired_code,
        sha=file_contents.sha,
        branch=branch_name
    )

    pr = repo.create_pull(
        title=f"🤖 [Auto-Repair] Automated fix for workflow #{run_id}",
        body="## 🤖 Autonomous Repair Report\n\nAutomated patch generated via Gemini API.",
        head=branch_name,
        base=base_branch
    )

    print(f"💎 SUCCESS! Pull Request opened: {pr.html_url}")

if __name__ == "__main__":
    run_repair_engine()
