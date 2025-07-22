import os
import json
from neo4j import GraphDatabase

class KnowledgeGraph:
    def __init__(self, uri, username, password, data_directory, text_processor, database="neo4j"):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.data_directory = data_directory
        self.text_processor = text_processor
        self.database = database
        self.json_nodes = {}
        with open("queries.json", "r") as f:
            self.queries = json.load(f)

    def close(self):
        self.driver.close()

    def load_json_files(self):
        for filename in os.listdir(self.data_directory):
            if filename.endswith(".json"):
                path = os.path.join(self.data_directory, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.json_nodes[data['path']] = data

    def create_node(self, tx, node):
        label = "Directory" if node['type'] == 'directory' else "File"
        embedding = self.text_processor.generate_embedding(node.get('content', ''))
        query = self.queries["create_node"].replace("{label}", label)
        tx.run(query,
               path=node['path'],
               name=node['name'],
               content=node.get('content', ''),
               embedding=embedding)

    def create_relationship(self, tx, parent_path=None, child_path=None,
                            parent_key=None, parent_value=None,
                            child_key=None, child_value=None):
        if parent_key and parent_value and child_key and child_value:
            # Create relationship based on key-value pairs (e.g., name)
            query = """
            MATCH (a {""" + parent_key + """: $parent_value}), (b {""" + child_key + """: $child_value})
            MERGE (a)-[:CONTAINS]->(b)
            """
            tx.run(query, parent_value=parent_value, child_value=child_value)
        elif parent_path and child_path:
            # Default relationship using path
            query = self.queries["create_relationship"]
            tx.run(query, parent_path=parent_path, child_path=child_path)
        else:
            raise ValueError("Insufficient parameters to create relationship")

    def build_graph(self):
        self.load_json_files()
        with self.driver.session() as session:
            session.run(self.queries["clear_graph"])
            for node in self.json_nodes.values():
                session.write_transaction(self.create_node, node)
            for parent_node in self.json_nodes.values():
                for child_id in parent_node.get('children', []):
                    # Find child node object by matching 'file_id'
                    child_node = next(
                        (n for n in self.json_nodes.values() if n.get("file_id") == child_id),
                        None
                    )
                    if child_node:
                        session.write_transaction(
                            self.create_relationship,
                            parent_key="name",
                            parent_value=parent_node["name"],
                            child_key="name",
                            child_value=child_node["name"]
                        )

    def get_all_document_nodes(self):
        return [
            {
                "path": node["path"],
                "name": node["name"],
                "content": node.get("content", "")
            }
            for node in self.json_nodes.values()
            if node.get("type") == "file"
        ]

    def run_query(self, query_name, parameters=None):
        query = self.queries.get(query_name)
        if not query:
            raise ValueError(f"Query '{query_name}' not found in queries.json")
        with self.driver.session() as session:
            result = session.run(query, **(parameters or {}))
            return [record.data() for record in result]

    def get_node_by_path(self, path):
        results = self.run_query("get_node_by_path", {"path": path})
        return results[0] if results else None