# Timeline: Graph-RAG Based Agentic System

This document outlines the tasks for the project focused on building a graph RAG from
product documentation using Python, Neo4j, and Streamlit.

Originally a 5-week internship project built by a 3-person team (Tasks 1-5 below). The
project was paused for roughly a year after the internship ended, then independently
revived, debugged, and extended into a fully working dual-backend agentic system
(Tasks 6-9 below).

## Original Internship Tasks

---

### Task 1: Documentation Parsing and JSON Node Creation
*   **Task ID:** T1
*   **Task Description:**
    *   Understand the structure of the product documentation located in the `/docs` directory.
    *   Design and implement a Python `DirectoryParser` class to recursively parse all Markdown (`.md`) files within the `/docs` directory and its subdirectories.
    *   For each Markdown file, extract its full content.
    *   Identify its hierarchical relationship (e.g., parent document, child documents) based on the directory structure.
    *   Generate a JSON representation for each parsed document. Each JSON object should represent a potential node in the knowledge graph.
    *   The JSON object should include at least:
        *   `name`: Name of the file or directory.
        *   `content`: Processed and clean textual content of the markdown file.
        *   `children`: An array of objects with keys - name and type (if any, based on subdirectories and documents).
    *   Store these JSON objects, as individual `.json` files in a new `/temp_data` directory.
*   **Assigned to:** Internship team
*   **Expected Delivery Date:** 11th June (Wed)
*   **Status:** DONE

---

### Task 2: Basic Knowledge Graph Construction in Neo4j
*   **Task ID:** T2
*   **Task Description:**
    *   Familiarize yourself with Neo4j graph database concepts: Nodes, Relationships, Properties, and the Cypher query language.
    *   Set up a local Neo4j instance.
    *   Design and implement a Python `KnowledgeGraph` class and corresponding methods to read the JSON files generated in Task T1.
    *   Design and implement a Python `TextProcessor` class to implement various NLP related methods like embedding generation, etc.
    *   For each JSON object:
        *   Create a corresponding Node in Neo4j (e.g., with a label like `File` or `Directory`).
        *   Store key information from the JSON (like `name`, `content`, `children`, `embedding`) as properties of this Neo4j node.
    *   Establish relationships between these nodes based on the hierarchical structure identified in Task T1. For example, create a `CONTAINS` relationship from a parent document node to its child document/directory nodes.
    *   The primary deliverable is a Neo4j database populated with nodes representing each document and directory along with relationships representing their basic directory structure.
*   **Assigned to:** Internship team
*   **Expected Delivery Date:** 18th June (Wed)
*   **Status:** DONE

---

### Task 3: Identifying and Creating Additional Semantic Links
*   **Task ID:** T3
*   **Task Description:**
    *   The goal of this task is to enrich the knowledge graph by adding non-hierarchical (semantic) links only between document nodes.
    *   Re-parse the content of the documents (from the JSON files).
    *   Implement a strategy to identify potential relationships between different documentation sections that are not explicitly defined by the directory structure.
    *   Design and implement a Python `DataProcessor` class that will contain methods to implement the Task T3.
    *   Define new relationship types in Neo4j to represent these discovered links (e.g., `RELATED_TO`).
*   **Assigned to:** Internship team
*   **Expected Delivery Date:** 25th June (Wed)
*   **Status:** DONE (originally) — **revisited during restart, see Task 7 below**

---

### Task 4: Knowledge Graph Retriever Implementation
*   **Task ID:** T4
*   **Task Description:**
    *   Design and implement a Python `GraphRAG` class.
    *   The `GraphRAG` class should:
        *   Establish a connection to the Neo4j database.
        *   Have a core method that accepts a user's natural language query (a string) as input.
        *   Implement logic to translate this user query into one or more Cypher queries to execute against the Neo4j graph. This might involve:
            *   Searching for nodes whose `content` property matches keywords from the user query.
            *   Leveraging the relationships (both hierarchical and semantic) to find connected/relevant information.
            *   (Optional, more advanced) If implementing text similarity for Task T3, you could embed the user query and find nodes with similar content embeddings.
        *   The method should retrieve the `content` of the Neo4j nodes that are deemed most relevant to the user's query.
        *   Consider how to rank or score the retrieved nodes/documents by relevance, if multiple results are found.
    *   The deliverable is the `GraphRAG` class, with clear documentation on how to use it and examples.
*   **Assigned to:** Internship team
*   **Expected Delivery Date:** 3rd July (Thursday)
*   **Status:** under review (at end of internship)

---

### Task 5: Streamlit UI for Demonstration
*   **Task ID:** T5
*   **Task Description:**
    *   Develop a user-friendly web interface using Streamlit to showcase the capabilities of the knowledge graph and retriever.
    *   The UI should allow an end-user to:
        *   Enter a natural language query related to the product documentation.
        *   View the search results retrieved by the `GraphRAG` class (from Task T4).
        *   Display the content of the relevant document sections in a readable format.
    *   Consider adding features like:
        *   Displaying metadata about the retrieved documents (e.g., source path, related topics).
        *   Visualizing parts of the knowledge graph related to the query or results (optional, can be complex).
        *   Basic error handling and user feedback.
    *   Ensure the UI is intuitive and effectively demonstrates the project's value in navigating and understanding the product documentation.
    *   The UI should primarily interact with the `GraphRAG` class built in Task T4.
*   **Assigned to:** Internship team
*   **Expected Delivery Date:** 7 July (Mon)
*   **Status:** Under Review (at end of internship)

---

## Restart Phase (Solo — Lalit Mittal, ~1 Year Later)

The project was reopened from the original team's codebase, the environment fully rebuilt
from scratch, and extended with a second, agentic RAG backend. All work in this section
(Tasks 6-9) was done independently by Lalit Mittal.

---

### Task 6: Environment Recovery and Stabilization
*   **Task ID:** T6
*   **Task Description:**
    *   Diagnosed and resolved a corrupted/mismatched dependency environment (numpy, scipy,
        scikit-learn, torch, thinc all installed with incompatible compiled wheels from a
        poisoned pip cache).
    *   Rebuilt the virtual environment from scratch with `--no-cache-dir` installs.
    *   Resolved a circular import between `main.py` and `ui/task1_ui.py` by extracting
        shared task-runner functions into a standalone `task_runners.py` module.
    *   Verified and re-tested the original parsing → graph-build → chat pipeline end to end.
*   **Status:** DONE

---

### Task 7: Knowledge Graph Data Quality Fixes
*   **Task ID:** T7
*   **Task Description:**
    *   Identified that `RELATED_TO` semantic links (Task 3) were never actually created in
        the live graph — NER on domain-specific test-case text yields too few entities for
        the existing Jaccard-similarity bandpass filter to produce links.
    *   Identified and worked around empty/missing `embedding` and `content` fields on
        `Requirement`/`AcceptanceCriteria` nodes, which caused `gds.similarity.cosine` to
        throw runtime errors on retrieval.
    *   Added defensive filtering (`size(n.embedding) = size($embedding)`) to the similarity
        query so retrieval degrades gracefully instead of crashing.
*   **Status:** DONE (similarity-query crash fixed) / **OPEN** (RELATED_TO link generation
    still needs improved entity extraction — see Roadmap in README)

---

### Task 8: CrewAI + Groq Agentic RAG Backend
*   **Task ID:** T8
*   **Task Description:**
    *   Added a second, independent RAG backend (`service/crewai_rag_main.py`) using a
        CrewAI `Agent`/`Task`/`Crew` pipeline backed by a Groq-hosted LLM (Qwen3-32B),
        alongside the original HuggingFace-based `GraphRAG` backend.
    *   Diagnosed and pinned around a confirmed upstream CrewAI bug
        ([crewAI#5886](https://github.com/crewAIInc/crewAI/issues/5886)) where newer CrewAI
        versions inject an Anthropic-specific `cache_breakpoint` field into messages sent to
        non-Anthropic providers, breaking Groq calls. Project pins `crewai==0.130.0` and
        `crewai-tools==0.42.0` to avoid this.
    *   Verified end-to-end: embedding → Neo4j similarity search → agent tool call → grounded
        LLM answer, tested via CLI.
*   **Status:** DONE

---

### Task 9: Dual-Backend Streamlit Chat UI
*   **Task ID:** T9
*   **Task Description:**
    *   Updated `ui/task4_ui.py` with a live radio-button toggle ("HuggingFace (GraphRAG)"
        vs "CrewAI + Groq") so either backend can answer the same question, selectable per
        question in the browser.
    *   Verified both backends return consistent, data-grounded answers on the same queries
        against the live Neo4j graph.
*   **Status:** DONE

---

## Roadmap (Not Yet Done)
*   Improve NER/entity extraction so `RELATED_TO` semantic links actually get created (Task 3
    revisit).
*   Backfill `content` for `Requirement`/`AcceptanceCriteria` nodes for richer embeddings.
*   Add prompt/context capture for the CrewAI backend in the UI (currently only implemented
    for the HuggingFace backend's "Prompt + context" expander).
*   Clean up development debug logging left in `crewai_rag_main.py`.