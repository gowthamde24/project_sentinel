import os
import time
from dotenv import load_dotenv
load_dotenv()
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

INDEX_NAME = "sentinel-docs"

sample_docs = [
    Document(page_content="ROS 2 SLAM Toolbox: If drift_x or drift_y exceeds 0.5 or cumulative drift exceeds 10.0, the SLAM module is considered to have lost tracking. Recommended action: Trigger a re-localization routine or restart the SLAM node.", metadata={"source": "ros2_slam_manual"}),
    Document(page_content="Hardware limits: Sustained power draw above 250W accompanied by CPU spikes >90% indicates a thermal throttling event or potential hardware failure. Recommended action: Throttle down perception nodes.", metadata={"source": "hardware_specs"}),
    Document(page_content="IMU Calibration: If Z-axis acceleration deviates from 9.8 by more than 1.0 m/s^2 while stationary, recalibration of the IMU is required.", metadata={"source": "imu_docs"})
]

def ingest_docs():
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    
    # Check if index exists, if not create it
    if INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
        print(f"Creating Pinecone index '{INDEX_NAME}'...")
        pc.create_index(
            name=INDEX_NAME,
            dimension=384, # HuggingFace all-MiniLM-L6-v2 dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        # Wait for index to be ready
        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)
        print("Index created successfully.")
    
    print("Ingesting sample technical documents into Pinecone...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    
    vectorstore.add_documents(sample_docs)
    print("Ingestion complete.")

if __name__ == "__main__":
    if "PINECONE_API_KEY" not in os.environ:
        print("Please set PINECONE_API_KEY before running ingestion.")
    else:
        ingest_docs()

