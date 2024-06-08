import os
import subprocess
import git
from git import Repo
import config
import custom
import requests
import json
import openai

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
    openai.api_key = config.OPENAI_KEY

    # Creating the messages array as in the conversational model
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content}
    ]

    # Using the Chat Completion endpoint
    response = openai.ChatCompletion.create(
        model=custom.LLM_MODEL,
        messages=messages,
        temperature=1,
        max_tokens=custom.MAX_TOKENS,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    # Assuming the response from OpenAI is structured with choices and message contents
    return response.choices[0].message['content'].strip()


def groqcloud_process(content, prompt):
    """ Process content using GroqCloud's API. """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQCLOUD_KEY}",
        "Content-Type": "application/json"
    }
    # Building messages with both the system prompt and the user content
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content}
    ]

    payload = {
        "model": f"{custom.LLM_MODEL}",
        "messages": messages,
        "temperature": 1,
        "max_tokens": custom.MAX_TOKENS,
        "top_p": 1,
        "stream": False,
        "stop": None
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        # Assuming the relevant content is in the first choice of the first message
        return response_data['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the GroqCloud API request: {e}")
        return content  # Return the original content if there's an error

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
