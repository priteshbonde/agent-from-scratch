# agent-from-scratch

An AI agent built by hand in plain Python, with no agent framework. It gains one new capability every week, and each week's results are measured.

| Week | Capability | Status |
|---|---|---|
| 1 | Tool execution: an agent loop that calls tools | ✅ done |
| 2 | Context management: long chats that stay fast | 🚧 in progress |
| 3 | Memory: remembers across sessions | ⏳ |
| 4 | Multi-agent: orchestrator + workers, benchmarked against a single agent | ⏳ |
| 5 | Evals: a hand-labelled benchmark with graders | ⏳ |
| 6 | Sandboxed code execution | ⏳ |
| 7 | Durable execution: survives a crash | ⏳ |
| 8 | Public API + SDK | ⏳ |

## How it works (Week 1)

```
task ──▶ model ──"call read_file('docs/faq.md')"──▶ run tool
           ▲                                          │
           └──────────── tool result ◀────────────────┘
           repeat until the model answers (or MAX_STEPS)
```

- `agent/loop.py`: the loop itself
- `agent/tools.py`: `list_dir`, `read_file`, `fetch_url`, all locked to `workspace/`
- `agent/llm.py`: the real model, plus a `FakeLLM` so tests cost nothing
- `agent/log.py`: every step goes to `runs/*.jsonl`
- `evals/`: 10 tasks with expected answers

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then put your key in .env
pytest -q                     # free, no key needed
python -m agent "How many .md files are in the docs folder?"
python -m evals.run_evals     # real model, costs a few cents
```

## Results

| Week | Eval score | Avg steps | Avg tokens/task | Notes |
|---|---|---|---|---|
| 1 | 10/10 | 2.4 | 2,263 | claude-haiku-5-5; 17 tool calls, 0 tool errors |

## Sample trace

Eval task 7: *"Which file in the docs folder says which Python version is required?"* 5 tool calls in 3 model calls.

```
step 1  list_dir  docs                     <- "what files are here?"
step 2  read_file docs/changelog.txt  ┐
        read_file docs/faq.md         │    <- 4 reads in ONE turn (parallel)
        read_file docs/intro.md       │
        read_file docs/setup.md       ┘
step 3  answer: "Python 3.12 or newer is in setup.md"
```

## Safety notes

- File tools resolve every path and refuse anything outside `workspace/`, including `../` and symlinks.
- `fetch_url` allows only http(s), with a 10 s timeout and truncated output.
- Tool errors go back to the model as `is_error` results instead of crashing the loop.
- The API key lives in `.env`, which is git-ignored.

## What I learned

- Used `yield`, which turns a function into generator, So even safety checks run late.
- The tools descriptions is used by model to understand working of the tool.
- tool results go back as a user message, all of them in one message
- why safe_path uses is_relative_to and not startswith
