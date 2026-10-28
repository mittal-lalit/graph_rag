import os
import json
from typing import List, Dict

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
from config.settings import (
    NEO4J_URI,
    NEO4J_USERNAME,
    NEO4J_PASSWORD,
    EMBEDDING_MODEL,
    HF_TOKEN,
    QA_MODEL,
)
from common.knowledge_graph import KnowledgeGraph
from common.text_processor import TextProcessor

class GraphRAG:
    """Initialize the Graph‑RAG pipeline, models, and Neo4j connection."""
    def __init__(
        self,
        hf_token: str | None = None,
        top_k: int = 3,
        neighbors_k: int = 3,
    ):
        self.top_k = top_k
        self.neighbors_k = neighbors_k
        self.hf_token = hf_token

        self.text_processor = TextProcessor(EMBEDDING_MODEL)
        self.knowledge_graph = KnowledgeGraph(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            data_directory=None,
            text_processor=self.text_processor,
        )
        self.llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.llm_model_name = QA_MODEL
        self.model_template = self.load_model_template(self.llm_model_name)

        self.chat_history: List[Dict[str, str]] = [] 
    def load_model_template(self, model_name: str) -> dict:
        """Load the JSON prompt template for the given model."""
        base_name = model_name.split("/")[-1].lower().replace(" ", "-")
        template_path = os.path.join("model_templates", f"{base_name}.json")
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Model template not found: {template_path}")
        with open(template_path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def generate_messages(
        self,
        model_name: str,
        user_query: str,
        retrieved_context: str,
    ) -> List[Dict[str, str]]:
        """Create chat messages using the model's prompt template and past Q&A history."""
        template = (
            self.model_template
            if model_name == self.llm_model_name
            else self.load_model_template(model_name)
        )

        system_prompt: str = template["system_prompt"]
        user_blocks: List[Dict[str, str]] = template["user_template"]

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        for pair in self.chat_history:
            messages.append({"role": "user", "content": pair["question"]})
            messages.append({"role": "assistant", "content": pair["answer"]})

        composed_user_content = "\n".join(
            block["text"]
            .replace("{context}", retrieved_context.strip())
            .replace("{question}", user_query.strip())
            for block in user_blocks
        )
        messages.append({"role": "user", "content": composed_user_content})

        return messages

    def chat_interface(self, user_query: str) -> str:
        """End‑to‑end: embed query, retrieve context, build prompt, query LLM, return answer."""
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
            visited_paths.add(path)

            main_node = self.knowledge_graph.get_node_by_path(path)
            if main_node:
                context_text += f"\n[{main_node['name']}]\n{main_node['content']}\n"

            neighbour_records = self.knowledge_graph.run_query(
                "get_neighbors", {"path": path}
            )[: self.neighbors_k]
            for record in neighbour_records:
                neighbour_path = record.get("path")
                if neighbour_path not in visited_paths:
                    visited_paths.add(neighbour_path)
                    neighbour_node = self.knowledge_graph.get_node_by_path(neighbour_path)
                    if neighbour_node:
                        context_text += (
                            f"\n[{neighbour_node['name']}]\n{neighbour_node['content']}\n"
                        )

        if not context_text.strip():
            return "No content available."

        messages = self.generate_messages(
            self.llm_model_name, user_query, context_text
        )
        response = self.llm_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=0.2,
            max_tokens=1500,
        )
        answer_text = response.choices[0].message.content.strip()
        print("\nAnswer:", answer_text)

        self.chat_history.append(
            {"question": user_query.strip(), "answer": answer_text}
        )
        while len(self.chat_history) > 5:
            self.chat_history.pop(0)

        return answer_text

    def clear_history(self):
        """Forget every stored Q&A turn."""
        self.chat_history.clear()

    def close(self):
        """Close the Neo4j driver."""
        self.knowledge_graph.close()
