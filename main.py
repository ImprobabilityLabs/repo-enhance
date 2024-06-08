import os
import subprocess
import git
from git import Repo
import config
import custom

def clone_repo(repo_url, branch_name):
    """ Clone a repository from a URL into a specified directory. """
    if os.path.exists("repo"):
        shutil.rmtree("repo")
    Repo.clone_from(repo_url, "repo", branch=branch_name)
    return "repo"

def process_file(file_path, prompt):
    """ Send file content to the LLM and get the modified content back. """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    modified_content = apply_llm(content, prompt)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

def apply_llm(content, prompt):
    """ Apply the language model to the content based on the prompt. """
    if custom.LLM_PROVIDER == "OpenAI":
        return openai_process(content, prompt)
    elif custom.LLM_PROVIDER == "GroqCloud":
        return groqcloud_process(content, prompt)
    else:
        return content

def openai_process(content, prompt):
    """ Process content using OpenAI's API. """
    import openai
    openai.api_key = config.OPENAI_KEY
    response = openai.Completion.create(
        engine=custom.LLM_MODEL,
        prompt=prompt + "\n\n" + content,
        max_tokens=2048
    )
    return response.choices[0].text.strip()

def groqcloud_process(content, prompt):
    """ Dummy function for GroqCloud processing. To be implemented. """
    return content  # Dummy return

def push_changes(destination_repo, destination_branch):
    """ Push changes to the destination repository. """
    repo = Repo("repo")
    repo.git.add(all=True)
    repo.git.commit('-m', 'Processed files with LLM')
    repo.git.push("origin", destination_branch)

def main():
    clone_repo(custom.SOURCE_REPO, custom.SOURCE_BRANCH)
    os.chdir("repo")
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):  # Assuming we're processing Python files
                process_file(os.path.join(root, file), custom.SYSTEM_PROMPT)
    push_changes(custom.DESTINATION_REPO, custom.DESTINATION_BRANCH)

if __name__ == "__main__":
    main()
