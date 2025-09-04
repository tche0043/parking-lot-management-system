import pymssql
from flask import current_app
import logging

class DatabaseConnector:
    def __init__(self):
        self.connection = None
    
    def get_connection(self):
        """Get database connection using current app config"""
        try:
            if self.connection is None or self._connection_closed():
                # Parse connection string for pymssql
                config = current_app.config
                self.connection = pymssql.connect(
                    server=config['DB_SERVER'],
                    user=config['DB_USERNAME'], 
                    password=config['DB_PASSWORD'],
                    database=config['DB_DATABASE'],
                    port=int(config.get('DB_PORT', 1433)),
                    timeout=30,
                    as_dict=True
                )
            return self.connection
        except Exception as e:
            current_app.logger.error(f"Database connection error: {str(e)}")
            raise
    
    def _connection_closed(self):
        """Check if connection is closed (pymssql doesn't have .closed attribute)"""
        if self.connection is None:
            return True
        try:
            # Try a simple query to check if connection is alive
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return False
        except:
            return True
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query and return results"""
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(as_dict=True)
            
            current_app.logger.info(f"Executing query: {query}")
            current_app.logger.info(f"Query params: {params}")
            current_app.logger.info(f"Fetch mode: {fetch}")
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                if query.strip().upper().startswith('SELECT'):
                    results = cursor.fetchall()
                    current_app.logger.info(f"Query returned {len(results)} rows")
                    return results
                else:
                    rowcount = cursor.rowcount
                    current_app.logger.info(f"Query affected {rowcount} rows")
                    return rowcount
            else:
                rowcount = cursor.rowcount
                current_app.logger.info(f"Before commit: Query affected {rowcount} rows")
                conn.commit()
                current_app.logger.info(f"Transaction committed successfully")
                return rowcount
                
        except Exception as e:
            current_app.logger.error(f"Query execution error: {str(e)}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def execute_transaction(self, queries_with_params):
        """Execute multiple queries in a transaction"""
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for query, params in queries_with_params:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
            
            conn.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Transaction error: {str(e)}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
    
    def close_connection(self):
        """Close database connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection = None

# Global database connector instance
db_connector = DatabaseConnector()