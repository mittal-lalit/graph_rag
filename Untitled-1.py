# alit@BALAJI MINGW64 /e/GraphReg/graph-rag (t7)
# $ streamlit run main.py -- --task ui

# python main.py --task task4

# how to check groq ai 

# import os
# from dotenv import load_dotenv

# load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")

# print("Key loaded:", bool(groq_api_key))
# print("Starts with:", groq_api_key[:8] if groq_api_key else None)

# from groq import Groq

# client = Groq(api_key=groq_api_key)

# try:
#     response = client.chat.completions.create(
#         model="llama-3.1-8b-instant",
#         messages=[{"role": "user", "content": "Say hello in one word."}]
#     )
#     print("SUCCESS. Response:", response.choices[0].message.content)
# except Exception as e:
#     print("FAILED:", e)





# crewai File
# from crewai import LLM, Agent, Task, Crew
# from crewai.tools import BaseTool
# from neo4j import GraphDatabase
# from typing import Any, Dict, List, Optional
# import json
# import os
# from dotenv import load_dotenv
# from sentence_transformers import SentenceTransformer

# # =========================
# # Load environment
# # =========================
# load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")

# # =========================
# # 1. Groq LLM setup
# # =========================
# groq_LLM = LLM(
#     model="groq/qwen/qwen3-32b",
#     api_key=groq_api_key,
# )

# # =========================
# # 2. Embedding Generator
# # =========================
# class TextProcessor:
#     def __init__(self):
#         self.model = SentenceTransformer("all-MiniLM-L6-v2")

#     def generate_embedding(self, text: str) -> List[float]:
#         return self.model.encode(text).tolist()

# # =========================
# # 3. Knowledge Graph from Neo4j
# # =========================
# class KnowledgeGraph:
#     def __init__(self, uri, username, password):
#         self.driver = GraphDatabase.driver(uri, auth=(username, password))

#     def run_query(self, name: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
#         with self.driver.session(database="neo4j") as session:
#             if name == "similarity_query":
#                 embedding = params["embedding"]
#                 top_k = params["top_k"]
#                 query = """
#                 MATCH (n:Node)
#                 WHERE exists(n.embedding)
#                 WITH n, gds.similarity.cosine(n.embedding, $embedding) AS score
#                 RETURN n.path AS path, score
#                 ORDER BY score DESC LIMIT $top_k
#                 """
#                 result = session.run(query, embedding=embedding, top_k=top_k)
#                 return [record.data() for record in result]

#             elif name == "get_neighbors":
#                 query = """
#                 MATCH (n { path: $path })-[:RELATED_TO]-(neighbor)
#                 RETURN neighbor.path AS path
#                 """
#                 result = session.run(query, path=params["path"])
#                 return [record.data() for record in result]

#         return []

#     def get_node_by_path(self, path: str) -> Optional[Dict[str, Any]]:
#         with self.driver.session(database="neo4j") as session:
#             query = """
#             MATCH (n { path: $path })
#             RETURN n.name AS name, n.content AS content
#             """
#             result = session.run(query, path=path)
#             record = result.single()
#             return record.data() if record else None

# # =========================
# # 4. RAG Backend
# # =========================
# class RAGBackend:
#     def __init__(self, text_processor: TextProcessor, knowledge_graph: KnowledgeGraph,
#                  top_k: int = 5, neighbors_k: int = 3):
#         self.text_processor = text_processor
#         self.knowledge_graph = knowledge_graph
#         self.top_k = top_k
#         self.neighbors_k = neighbors_k

#     def chat_interface(self, user_query: str) -> str:
#         print(f"\nProcessing query: {user_query}")
#         query_embedding = self.text_processor.generate_embedding(user_query)

#         top_nodes = self.knowledge_graph.run_query(
#             "similarity_query", {"embedding": query_embedding, "top_k": self.top_k}
#         )
#         if not top_nodes:
#             return "No answer found."

#         context_text = ""
#         visited_paths: set[str] = set()

#         for node in top_nodes:
#             path = node.get("path")
#             if path is None:
#                 continue
#             visited_paths.add(path)

#             main_node = self.knowledge_graph.get_node_by_path(path)
#             if main_node:
#                 context_text += f"\n[{main_node['name']}]\n{main_node.get('content', '')}\n"

#             neighbor_records = self.knowledge_graph.run_query(
#                 "get_neighbors", {"path": path}
#             )[: self.neighbors_k]

#             for record in neighbor_records:
#                 neighbor_path = record.get("path")
#                 if neighbor_path and neighbor_path not in visited_paths:
#                     visited_paths.add(neighbor_path)
#                     neighbor_node = self.knowledge_graph.get_node_by_path(neighbor_path)
#                     if neighbor_node:
#                         context_text += f"\n[{neighbor_node['name']}]\n{neighbor_node.get('content', '')}\n"

#         prompt = f"""You must answer ONLY in English.
# Context:
# {context_text}

# Question: {user_query}

# Answer in simple English:"""

#         return groq_LLM.call(prompt)

# # =========================
# # 5. CrewAI Tool
# # =========================
# class ChatWithGraphTool(BaseTool):
#     name: str = "chat_with_graph"
#     description: str = "Run the full RAG pipeline over the knowledge graph to answer a question."

#     def _run(self, query: str) -> str:
#         answer = rag_backend.chat_interface(query)
#         return json.dumps({"answer": answer}, indent=2)

# # Instantiate tool
# rag_backend = RAGBackend(
#     text_processor=TextProcessor(),
#     knowledge_graph=KnowledgeGraph(),
#     top_k=5,
#     neighbors_k=3
# )
# chat_tool = ChatWithGraphTool()

# # =========================
# # 6. Agent + Task
# # =========================
# SYSTEM_PROMPT = """
# You are a helpful assistant. You must ALWAYS answer in English.
# To answer the user, ALWAYS call the 'chat_with_graph' tool with the exact user query.
# Return the tool's answer as your final answer (do not invent extra info).
# """

# agent = Agent(
#     role="Graph RAG Agent",
#     goal="Answer user questions using the knowledge graph RAG pipeline.",
#     backstory="You only answer using the database via the chat_with_graph tool.",
#     llm=groq_LLM,
#     tools=[chat_tool],
#     verbose=False,
#     allow_delegation=False,
#     system_prompt=SYSTEM_PROMPT
# )

# task = Task(
#     description="User question: '{user_query}'. Call chat_with_graph and return the English answer.",
#     expected_output="A concise English answer based only on the RAG pipeline result.",
#     agent=agent
# )

# crew = Crew(agents=[agent], tasks=[task], verbose=False)

# # =========================
# # 7. Interactive CLI
# # =========================
# if __name__ == "__main__":
#     while True:
#         try:
#             user_query = input("\nAsk your question (type 'exit' to quit): ")
#         except (EOFError, KeyboardInterrupt):
#             print("\nGoodbye!")
#             break
#         if user_query.strip().lower() == "exit":
#             print("Goodbye!")
#             break

#         result = crew.kickoff(inputs={"user_query": user_query})
#         print("Answer:", result)





# task4

# import json
# import streamlit as st
# from service.graph_rag import GraphRAG
# from config import settings
# import sentence_transformers as st_models
 
# original_sentence_transformer = st_models.SentenceTransformer
 
# def sentence_transformer_cpu(model_name, *args, **kwargs):
#     """Force model to load on CPU."""
#     kwargs["device"] = "cpu"
#     return original_sentence_transformer(model_name, *args, **kwargs)
 
# st_models.SentenceTransformer = sentence_transformer_cpu
 
# def rerun():
#     """Force Streamlit to rerun the app."""
#     if hasattr(st, "rerun"):
#         st.rerun()
#     elif hasattr(st, "experimental_rerun"):
#         st.experimental_rerun()
 
# def get_rag() -> GraphRAG:
#     """Get or create the GraphRAG instance in session state."""
#     if "rag" not in st.session_state:
#         st.session_state.rag = GraphRAG(
#             hf_token=settings.HF_TOKEN,
#             top_k=3,
#             neighbors_k=3,
#         )
#         st.session_state.chat_turns = []
#     return st.session_state.rag
 
# def render():
#     """Render the chat UI and handle user interaction."""
#     st.title("Ask Me Anything About Your Docs!")
#     rag = get_rag()
 
#     for question, answer, prompt in st.session_state.chat_turns:
#         with st.chat_message("user"):
#             st.write(question)
#         with st.chat_message("assistant"):
#             st.write(answer)
#             with st.expander("📝 Prompt + context", expanded=False):
#                 st.code(prompt, language="json")
 
#     user_query = st.chat_input("Ask your question…")
 
#     if user_query:
#         captured = {"prompt": None}
#         original_generate = rag.generate_messages
 
#         def capture_messages(*args, **kwargs):
#             """Capture the prompt used to generate the response."""
#             captured["prompt"] = original_generate(*args, **kwargs)
#             return captured["prompt"]
 
#         rag.generate_messages = capture_messages
 
#         with st.spinner("Thinking…"):
#             assistant_answer = rag.chat_interface(user_query)
 
#         rag.generate_messages = original_generate
 
#         prompt_json = (
#             json.dumps(captured["prompt"], indent=2, ensure_ascii=False)
#             if captured["prompt"]
#             else "⟨prompt not captured⟩"
#         )
 
#         st.session_state.chat_turns.append((user_query, assistant_answer, prompt_json))
#         rerun()
 
#     if st.session_state.get("chat_turns") and st.button("🗑️ Clear chat"):
#         """Clear the chat history and reset GraphRAG memory."""
#         st.session_state.chat_turns = []
#         st.session_state.rag.clear_history()
#         rerun()