from typing import List, Dict, Any

class SearchTools:

    def __init__(self, index):
        self.index = index

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search the FAQ database for entries matching the given query.
    
        Args:
            query (str): Search query text to look up in the course FAQ.
    
        Returns:
            List[Dict[str, Any]]: A list of search result entries, each containing relevant metadata.
        """
        boost = {'question': 3.0, 'section': 0.5}
    
        results = self.index.search(
            query=query,
            filter_dict={'course': 'data-engineering-zoomcamp'},
            boost_dict=boost,
            num_results=5,
        )
    
        return results

    def add_entry(self, question: str, answer: str) -> None:
        """
        Add a new entry to the FAQ database.
    
        Args:
            question (str): The question to be added to the FAQ database.
            answer (str): The corresponding answer to the question.
        """
        doc = {
            'question': question,
            'text': answer,
            'section': 'user added',
            'course': 'data-engineering-zoomcamp'
        }
        self.index.append(doc)