import os
import logging
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class Neo4jConnection:
    """A context-aware Neo4j database connection manager."""
    
    def __init__(self):
        self.uri = os.environ.get("NEO4J_URI")
        self.username = os.environ.get("NEO4J_USERNAME")
        self.password = os.environ.get("NEO4J_PASSWORD")
        self.driver: Optional[Driver] = None

    def connect(self) -> Driver:
        """Establishes and returns a connection to the Neo4j database."""
        if self.driver is not None:
            logger.info("Neo4j driver is already initialized.")
            return self.driver

        # Validate all required environment variables exist
        required_vars = {
            "NEO4J_URI": self.uri,
            "NEO4J_USERNAME": self.username,
            "NEO4J_PASSWORD": self.password
        }
        
        for name, value in required_vars.items():
            if not value:
                error_msg = f"Missing environment variable: {name}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        try:
            logger.info("Connecting to Neo4j...")
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            
            # Verify connectivity to fail early if invalid credentials or endpoint
            self.driver.verify_connectivity()
            logger.info("Connected successfully.")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to establish Neo4j connection: {e}", exc_info=True)
            self.driver = None
            raise

    def close(self) -> None:
        """Closes the Neo4j connection and cleans up resources."""
        if self.driver:
            try:
                logger.info("Closing Neo4j connection...")
                self.driver.close()
                logger.info("Neo4j connection closed.")
            except Exception as e:
                logger.error(f"Error while closing Neo4j connection: {e}", exc_info=True)
            finally:
                self.driver = None
        else:
            logger.info("No active Neo4j connection to close.")

    def execute_query(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None, 
        database: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Executes a Cypher query and returns the results as a list of dictionaries.
        
        Args:
            query (str): Cypher query string.
            parameters (dict, optional): Map of query parameters.
            database (str, optional): Target database name.
            
        Returns:
            List[Dict[str, Any]]: Query results formatted as list of key-value dictionaries.
        """
        if not self.driver:
            logger.error("Attempted to execute query without active driver connection.")
            raise RuntimeError("Database connection not established. Please call connect() first.")

        parameters = parameters or {}
        try:
            with self.driver.session(database=database) as session:
                result = session.run(query, **parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {query}. Error: {e}", exc_info=True)
            raise

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
