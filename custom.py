SOURCE_REPO = "git@github.com:ImprobabilityLabs/pandas-ta-cudf.git"
SOURCE_BRANCH = "main"

DESTINATION_REPO = "git@github.com:ImprobabilityLabs/pandas-ta-cudf.git"
DESTINATION_BRANCH = "enhanced-test"

LLM_MODEL = "llama3-70b-8192"
LLM_PROVIDER = "GroqCloud"  # Options: "OpenAI", "GroqCloud"
MAX_TOKENS = 4096

LLM_WAIT=2

SYSTEM_PROMPT = "Refactor the following code for better performance and readability:"
