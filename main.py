import os
import subprocess
import git
from git import Repo
import config
import custom
import requests
import json
import openai
import time
import shutil  
import ast
import astor

def clone_repo(repo_url, branch_name):
    """ Clone a repository from a URL into a specified directory. """
    if os.path.exists("repo"):
        shutil.rmtree("repo")
    print(f"Cloning repository from {repo_url}...")
    Repo.clone_from(repo_url, "repo", branch=branch_name)
    return "repo"

def parse_python_functions(content):
    """ Parse Python content into functions and other code parts using AST. """
    tree = ast.parse(content)
    functions = []
    other_parts = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            functions.append(node)
        else:
            other_parts.append(node)

    return functions, other_parts

def process_file(file_path, prompt):
    """ Send file content to the LLM and get the modified content back, function by function or as a whole piece based on file length. """
    print(f"Processing file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    if len(content.split('\n')) > 175:  # Check if file has more than 175 lines
        functions, other_parts = parse_python_functions(content)
        processed_content = [astor.to_source(part) for part in other_parts]  # Process non-function parts as is

        for function in functions:
            original_function_code = astor.to_source(function)
            modified_function_code = apply_llm(original_function_code, prompt)
            processed_content.append(modified_function_code)
        processed_content = '\n\n'.join(processed_content)
    else:
        processed_content = apply_llm(content, prompt)  # Process the entire content as one piece

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(processed_content)
    print(f"Finished processing {file_path}")

def apply_llm(content, prompt):
    """ Apply the language model to the content based on the prompt. """
    if custom.LLM_PROVIDER == "OpenAI":
        result = openai_process(content, prompt)
    elif custom.LLM_PROVIDER == "GroqCloud":
        result = groqcloud_process(content, prompt)
    else:
        result = content
    time.sleep(custom.LLM_WAIT)  # Delay between API calls to avoid overloading
    return result

def openai_process(content, prompt):
    """ Process content using OpenAI's API. """
    openai.api_key = config.OPENAI_KEY
    print("Sending content to OpenAI...")
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
    print("Received response from OpenAI.")
    # Assuming the response from OpenAI is structured with choices and message contents
    return response.choices[0].message['content'].strip()

def groqcloud_process(content, prompt):
    """ Process content using GroqCloud's API with retry on rate limit errors (HTTP 429). """
    print("Sending content to GroqCloud...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.GROQCLOUD_KEY}",
        "Content-Type": "application/json"
    }
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
    
    max_retries = 3  # Set the maximum number of retries
    retry_delay = 15  # Set the delay in seconds between retries

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            print("Received response from GroqCloud.")
            return response_data['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"HTTP error occurred: {e}")
                break  # Break the loop for non-retryable HTTP errors
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the GroqCloud API request: {e}")
            break  # Break the loop for other types of request errors
    return content  # Return the original content if all retries fail

def push_changes(destination_repo, destination_branch):
    """ Push changes to the destination repository. """
    print("Committing changes and pushing to the repository...")
    print(f"Current directory: {os.getcwd()}")  # Print current working directory to debug
    try:
        repo = Repo('.')  # Assuming the current working directory is the root of the repository
        current_branch = repo.active_branch
        if destination_branch != current_branch.name:
            if destination_branch not in repo.heads:
                # Create new branch locally if it doesn't exist
                new_branch = repo.create_head(destination_branch)
                new_branch.checkout()
            else:
                # Checkout the existing local branch
                repo.heads[destination_branch].checkout()
        # Set the upstream to the new remote branch
        repo.git.push('--set-upstream', 'origin', destination_branch)
        repo.git.add(all=True)
        repo.git.commit('-m', 'Processed files with LLM')
        repo.git.push("origin", destination_branch)
        print("Pushed changes successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    try:
        # Change to the root directory where the script should run
        os.chdir('/opt/improbability/repo-enhance')
        print("Changed to script's root directory.")

        # Clone or pull the latest changes from the source repository
        if not os.path.exists("repo"):
            clone_repo(custom.SOURCE_REPO, custom.SOURCE_BRANCH)
        os.chdir("repo")  # Change directory to the cloned repo
        print(f"Changed to repository directory: {os.getcwd()}")

        # Traverse the directory tree and process Python files, skipping hidden directories
        for root, dirs, files in os.walk("."):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            print(f"Entering directory: {root}")
            for file in files:
                if file.endswith(".py"):  # Assuming we're processing Python files
                    file_path = os.path.join(root, file)
                    print(f"Processing file: {file_path}")
                    process_file(file_path, custom.SYSTEM_PROMPT)

        # Push the changes to the destination repository
        push_changes(custom.DESTINATION_REPO, custom.DESTINATION_BRANCH)
    except Exception as e:
        print(f"An error occurred: {e}")
        
if __name__ == "__main__":
    main()
