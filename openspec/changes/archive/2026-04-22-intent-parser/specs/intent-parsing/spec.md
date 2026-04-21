## ADDED Requirements

### Requirement: GitHubIntent dataclass defines the stable output schema

The module `src/ghibli/intent.py` SHALL define a frozen dataclass `GitHubIntent` with the following fields:
- `endpoint: str` — the GitHub REST API path (e.g., `/search/repositories`)
- `method: str` — the HTTP method in uppercase (e.g., `"GET"`)
- `params: dict[str, str]` — query parameters as string key-value pairs
- `description: str` — a human-readable description of the interpreted intent

The dataclass SHALL be frozen (immutable after creation).

#### Scenario: GitHubIntent is constructable with required fields

- **WHEN** code creates `GitHubIntent(endpoint="/search/repositories", method="GET", params={"q": "python stars:>1000"}, description="Search Python repos")`
- **THEN** all four fields are accessible as attributes

#### Scenario: GitHubIntent is immutable

- **WHEN** code attempts to assign a new value to any field on an existing `GitHubIntent` instance
- **THEN** a `FrozenInstanceError` (or `dataclasses.FrozenInstanceError`) is raised

#### Scenario: GitHubIntent params default to empty dict

- **WHEN** code creates `GitHubIntent` with `params={}` 
- **THEN** `intent.params` equals `{}`

### Requirement: parse_intent converts natural language to GitHubIntent

The function `parse_intent(query: str) -> GitHubIntent` in `src/ghibli/intent.py` SHALL call the Gemini 2.5 Flash API with the user's query and return a `GitHubIntent` constructed from the structured JSON response.

#### Scenario: Common search query is parsed correctly

- **WHEN** `parse_intent("find the most starred Python repositories")` is called
- **THEN** the returned `GitHubIntent.endpoint` is `"/search/repositories"`, `method` is `"GET"`, and `params` contains a `"q"` key with a value related to Python

#### Scenario: Issue listing query is parsed correctly

- **WHEN** `parse_intent("list open issues in the facebook/react repo")` is called
- **THEN** the returned `GitHubIntent.endpoint` contains `"/repos/facebook/react/issues"` and `params` contains `{"state": "open"}`

#### Scenario: Repository info query is parsed correctly

- **WHEN** `parse_intent("show me info about the torvalds/linux repo")` is called
- **THEN** the returned `GitHubIntent.endpoint` is `"/repos/torvalds/linux"` and `method` is `"GET"`

### Requirement: Authentication resolved from environment at call time

The function `parse_intent` SHALL support two mutually exclusive authentication modes determined at call time by reading environment variables:

1. **API Key mode**: activated when `GEMINI_API_KEY` is set. The client SHALL be constructed as `genai.Client(api_key=os.environ["GEMINI_API_KEY"])`.
2. **Vertex AI mode**: activated when `VERTEX_PROJECT` is set (and `GEMINI_API_KEY` is not set). The client SHALL be constructed as `genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"], location=os.environ.get("VERTEX_LOCATION", "us-central1"))`. Authentication relies on Google Application Default Credentials (ADC).

If neither `GEMINI_API_KEY` nor `VERTEX_PROJECT` is set, the function SHALL raise `IntentParseError` with the message `"No Gemini auth configured: set GEMINI_API_KEY or VERTEX_PROJECT"`.

`GEMINI_API_KEY` SHALL take precedence when both variables are set.

#### Scenario: API key mode used when GEMINI_API_KEY is set

- **WHEN** `GEMINI_API_KEY` is set in the environment and `VERTEX_PROJECT` is not set
- **THEN** `parse_intent()` constructs the client with the API key and makes the call without error

#### Scenario: Vertex AI mode used when VERTEX_PROJECT is set

- **WHEN** `VERTEX_PROJECT` is set and `GEMINI_API_KEY` is not set
- **THEN** `parse_intent()` constructs the client with `vertexai=True` and the project ID

#### Scenario: GEMINI_API_KEY takes precedence over VERTEX_PROJECT

- **WHEN** both `GEMINI_API_KEY` and `VERTEX_PROJECT` are set
- **THEN** `parse_intent()` uses API key mode (not Vertex AI mode)

#### Scenario: Vertex AI mode uses VERTEX_LOCATION when set

- **WHEN** `VERTEX_PROJECT="my-project"` and `VERTEX_LOCATION="asia-east1"` are set
- **THEN** the client is constructed with `location="asia-east1"`

#### Scenario: Vertex AI mode defaults location to us-central1

- **WHEN** `VERTEX_PROJECT` is set and `VERTEX_LOCATION` is not set
- **THEN** the client is constructed with `location="us-central1"`

#### Scenario: No auth configured raises IntentParseError

- **WHEN** neither `GEMINI_API_KEY` nor `VERTEX_PROJECT` is set
- **THEN** `IntentParseError` is raised with message `"No Gemini auth configured: set GEMINI_API_KEY or VERTEX_PROJECT"`

### Requirement: Unparseable intent raises IntentParseError

When the Gemini API response cannot be mapped to a valid `GitHubIntent` (malformed JSON, missing required fields, or non-GitHub API endpoint), `parse_intent` SHALL raise `IntentParseError` with a message that includes the original query.

#### Scenario: Gibberish input raises IntentParseError

- **WHEN** `parse_intent("xkcd 1234 asdf!!")` is called and Gemini cannot produce a valid GitHub endpoint
- **THEN** `IntentParseError` is raised

#### Scenario: Non-GitHub query raises IntentParseError

- **WHEN** `parse_intent("what is the weather in Tokyo")` is called
- **THEN** `IntentParseError` is raised with the original query in the message

### Requirement: Gemini API uses JSON-mode structured output

The Gemini API call SHALL use the `response_mime_type="application/json"` parameter and a system prompt that specifies the exact JSON schema matching `GitHubIntent` fields. This ensures the output schema is stable and parseable without heuristics.

#### Scenario: Response is always valid JSON

- **WHEN** `parse_intent()` receives a response from Gemini
- **THEN** the response body is valid JSON that `json.loads()` can parse without error

#### Scenario: Schema fields match GitHubIntent

- **WHEN** the Gemini response JSON is parsed
- **THEN** it contains exactly the keys `"endpoint"`, `"method"`, `"params"`, and `"description"`
