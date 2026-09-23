# Project: Graph-RAG Based Agentic Test Case System (CAMS)

A knowledge-graph-powered RAG system that parses Markdown documentation and Excel-based
requirement/acceptance-criteria/test-case sheets into a Neo4j graph, enriches it with semantic
links, and exposes it through a Streamlit chat interface backed by **two switchable LLM
pipelines** — HuggingFace and CrewAI + Groq.

Originally built during a 5-week internship; restarted and fully revived as a solo project a
year later, including a from-scratch environment rebuild and several pipeline fixes (see
"Known Issues & Fixes" below).

## Project Goals
- Parse Markdown documentation and Excel test-case sheets into structured JSON data.
- Construct a hierarchical knowledge graph in Neo4j (`Requirement` → `AcceptanceCriteria` → `TestCase`).
- Enrich the graph with NER-based semantic links between nodes (`RELATED_TO`).
- Generate embeddings per node and retrieve relevant context via vector similarity search.
- Expose retrieval through **two parallel RAG backends**:
  - HuggingFace Inference API (`service/graph_rag.py`)
  - CrewAI agent + Groq-hosted LLM (`service/crewai_rag_main.py`)
- Provide a Streamlit UI with document parsing, graph visualization, and a chat interface
  that can switch between both backends live.

## Technology Stack
- **Programming Language:** Python 3.11
- **Graph Database:** Neo4j 5+ (with the **GDS — Graph Data Science plugin** installed, required for `gds.similarity.cosine`)
- **NLP / Embeddings:** spaCy (NER), sentence-transformers (`all-MiniLM-L6-v2`)
- **LLM Backends:** HuggingFace `InferenceClient`, CrewAI `Agent`/`Task`/`Crew` + Groq (Qwen3-32B)
- **User Interface:** Streamlit (with `pyvis` for graph visualization)
- **Documentation Formats:** Markdown (`.md`), Excel (`.xlsx`)

## Getting Started

### 1. Environment setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
python -m spacy download en_core_web_sm
```

> **Tip:** if you hit `cp3XX` wheel mismatches (numpy/scipy/sklearn import errors mentioning
> the wrong CPython tag), your pip cache is poisoned — delete `venv/`, run `pip cache purge`,
> and reinstall from a clean venv created from the **project root** (not a subfolder).

### 2. Neo4j setup
- Install Neo4j Desktop (or run via Docker) — Neo4j 5+.
- **Install the Graph Data Science (GDS) plugin** on your database — required for the
  similarity search query (`gds.similarity.cosine`). In Neo4j Desktop: select your DB →
  Plugins tab → install "Graph Data Science Library".
- Verify with: `CALL gds.version()` in Neo4j Browser.

### 3. Environment variables
Create a `.env` file in the project root:
```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
HF_TOKEN=your_huggingface_token
GROQ_API_KEY=your_groq_api_key
```
Never commit `.env` or hardcode credentials in source files.

### 4. Run the pipeline (CLI)
```bash
python main.py --task task1   # parse docs/Excel -> temp_data/*.json
python main.py --task task2   # build Neo4j graph + NER semantic linking
python main.py --task task4   # interactive CLI chat (HuggingFace backend)
python -m service.crewai_rag_main   # interactive CLI chat (CrewAI + Groq backend)
```

### 5. Run the UI
```bash
streamlit run main.py -- --task ui
```
Navigate to the **Chat Interface** tab and use the radio toggle to switch between
"HuggingFace (GraphRAG)" and "CrewAI + Groq" for any question.

## Project Structure
```
common/
  directory_parser.py    # Markdown + Excel -> structured JSON
  knowledge_graph.py      # JSON -> Neo4j nodes/relationships + embeddings
  data_processor.py       # spaCy NER + Jaccard similarity -> RELATED_TO links
  text_processor.py       # embedding generation (sentence-transformers)
service/
  graph_rag.py             # HuggingFace-based RAG backend
  crewai_rag_main.py       # CrewAI agent + Groq-based RAG backend
ui/
  home_ui.py, task1_ui.py, task2_ui.py, task4_ui.py
config/
  settings.py              # central config (.env-backed)
task_runners.py             # task1/task2/task4 entry points (kept separate from main.py
                             # to avoid a circular import with ui/task1_ui.py)
main.py                      # CLI entrypoint + Streamlit app shell
docs/                         # raw Markdown documentation
test_cases/                   # raw Excel requirement/AC/test-case sheets
temp_data/                    # generated intermediate JSON (gitignored)
```

## Known Issues & Fixes Applied During Restart
- **`RELATED_TO` links are not currently generated** — Task 2's NER-based entity linking
  finds very few/no named entities in domain-specific test-case text (banking jargon like
  "Min Daily Balance" isn't recognized well by general-purpose NER models). Both RAG
  backends still work via direct vector similarity search; graph-traversal context
  (`get_neighbors`) currently returns nothing extra. Improving entity extraction or lowering
  similarity thresholds is a good next step.
- **Some nodes have empty `content`/`embedding` fields** — primarily `Requirement` and
  `AcceptanceCriteria` nodes that never received a `content` field during parsing. The
  similarity query filters these out (`WHERE n.embedding IS NOT NULL AND size(n.embedding) = size($embedding)`)
  to avoid `gds.similarity.cosine` errors, but richer content here would improve retrieval.
- **CrewAI 1.14.x has a confirmed bug** (`cache_breakpoint` injected into messages for
  non-Anthropic providers — [crewAI#5886](https://github.com/crewAIInc/crewAI/issues/5886))
  that breaks Groq/OpenAI-compatible providers. This project pins `crewai==0.130.0` and
  `crewai-tools==0.42.0` to avoid it.
- **Circular import** existed between `main.py` and `ui/task1_ui.py` (each imported from the
  other). Resolved by extracting `run_task_1`/`run_task_2`/`run_task_4_cli` into a separate
  `task_runners.py` module that both files import from independently.

## Roadmap / Possible Next Steps
- Improve NER/entity extraction so `RELATED_TO` semantic links actually get created.
- Backfill `content` for `Requirement`/`AcceptanceCriteria` nodes for richer embeddings.
- Add prompt/context capture for the CrewAI backend in the UI (currently only implemented
  for the HuggingFace backend's "Prompt + context" expander).
- Clean up debug logging left in `crewai_rag_main.py` from development.