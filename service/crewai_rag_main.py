from crewai import LLM, Agent, Task, Crew
from crewai.tools import BaseTool
from typing import Any, Dict, List, Optional
import json

# =========================
# 1) LLM (same as yours)
# =========================
huggingface_llm = LLM(
    model="huggingface/together/meta-llama/Llama-4-Scout-17B-16E-Instruct",
    api_key="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",
)

# =========================
# 2) Your RAG backend (plug your own implementations)
# =========================
# ---- Replace these stubs with your real classes ----
class TextProcessor:
    def generate_embedding(self, text: str) -> List[float]:
        # TODO: return a real embedding
        return [0.0] * 768

class KnowledgeGraph:
    def run_query(self, name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # TODO: call your Neo4j / Graph DB (similarity_query, get_neighbors)
        return []
    def get_node_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        # TODO: fetch node by path from your DB
        return None
# ----------------------------------------------------

class RAGBackend:
    def __init__(self, text_processor: TextProcessor, knowledge_graph: KnowledgeGraph,
                 top_k: int = 5, neighbors_k: int = 3):
        self.text_processor = text_processor
        self.knowledge_graph = knowledge_graph
        self.top_k = top_k
        self.neighbors_k = neighbors_k

    def chat_interface(self, user_query: str) -> str:
        """Your exact logic, just dropped in."""
        print(f"\nProcessing query: {user_query}")

        query_embedding = self.text_processor.generate_embedding(user_query)
        top_nodes = self.knowledge_graph.run_query(
            "similarity_query", {"embedding": query_embedding, "top_k": self.top_k}
        )
        if not top_nodes:
            return "No answer found."

        context_text = ""
        visited_paths: set[str] = set()

        for node in top_nodes:
            path = node.get("path")
            if path is None:
                continue
            visited_paths.add(path)

            main_node = self.knowledge_graph.get_node_by_path(path)
            if main_node:
                context_text += f"\n[{main_node['name']}]\n{main_node.get('content', '')}\n"

            neighbour_records = self.knowledge_graph.run_query(
                "get_neighbors", {"path": path}
            )[: self.neighbors_k]

            for record in neighbour_records:
                neighbour_path = record.get("path")
                if neighbour_path and neighbour_path not in visited_paths:
                    visited_paths.add(neighbour_path)
                    neighbour_node = self.knowledge_graph.get_node_by_path(neighbour_path)
                    if neighbour_node:
                        context_text += f"\n[{neighbour_node['name']}]\n{neighbour_node.get('content', '')}\n"

        # Now ask the LLM to answer using the built context (English only)
        prompt = f"""You must answer ONLY in English.
Context:
{context_text}

Question: {user_query}

Answer in simple English:"""

        return huggingface_llm.call(prompt)

# Instantiate with YOUR real objects
rag_backend = RAGBackend(
    text_processor=TextProcessor(),       # <-- replace with your real one
    knowledge_graph=KnowledgeGraph(),     # <-- replace with your real one
    top_k=5,
    neighbors_k=3
)

# =========================
# 3) Single CrewAI tool
# =========================
class ChatWithGraphTool(BaseTool):
    name: str = "chat_with_graph"
    description: str = "Run the full RAG pipeline over the knowledge graph to answer a question."

    def _run(self, query: str) -> str:
        answer = rag_backend.chat_interface(query)
        return json.dumps({"answer": answer}, indent=2)

chat_tool = ChatWithGraphTool()

# =========================
# 4) Agent + Task
# =========================
SYSTEM_PROMPT = """
You are a helpful assistant. You must ALWAYS answer in English.
To answer the user, ALWAYS call the 'chat_with_graph' tool with the exact user query.
Return the tool's answer as your final answer (do not invent extra info).
"""

agent = Agent(
    role="Graph RAG Agent",
    goal="Answer user questions using the knowledge graph RAG pipeline.",
    backstory="You only answer using the database via the chat_with_graph tool.",
    llm=huggingface_llm,
    tools=[chat_tool],
    verbose=False,
    allow_delegation=False,
    system_prompt=SYSTEM_PROMPT
)

task = Task(
    description="User question: '{user_query}'. Call chat_with_graph and return the English answer.",
    expected_output="A concise English answer based only on the RAG pipeline result.",
    agent=agent
)

crew = Crew(agents=[agent], tasks=[task], verbose=False)

# =========================
# 5) Interactive loop
# =========================
if __name__ == "__main__":
    while True:
        try:
            user_query = input("\nAsk your question (type 'exit' to quit): ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_query.strip().lower() == "exit":
            print("Goodbye!")
            break

        result = crew.kickoff(inputs={"user_query": user_query})
        print("Answer:", result)
