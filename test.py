from common.knowledge_graph import KnowledgeGraph
from common.text_processor import TextProcessor
from config import settings

processor = TextProcessor()
kg = KnowledgeGraph(
    uri=settings.NEO4J_URI,
    username=settings.NEO4J_USERNAME,
    password=settings.NEO4J_PASSWORD,
    data_directory=settings.DATA_DIRECTORY,
    text_processor=processor
)

kg.build_graph()
