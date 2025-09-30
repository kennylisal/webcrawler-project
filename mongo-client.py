from pymongo import MongoClient

# Connect to MongoDB
client = None
try:
    # Use the same connection string as in mongosh
    client = MongoClient('mongodb://localhost:27017/')

    # Access the same database used in mongosh
    db = client['test_database_x']
    print("Connected to MongoDB successfully!")

    # Access the same collection used in mongosh
    collection = db['test_collection']

    # Example: Insert a new document
    new_document = {"name": "Jane Doe", "age": 25, "city": "Los Angeles"}
    collection.insert_one(new_document)
    print("Inserted a document into the collection.")

    # Example: Query all documents
    print("Documents in test_collection:")
    for doc in collection.find():
        print(doc)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    if client is not None:
        client.close()
    print("MongoDB connection closed.")