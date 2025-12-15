
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")


# In[13]:


# Define stopwords for English
stopwords = [
    "a","about","above","after","again","against","all","am","an","and","any",
    "are","aren","aren't","as","at","be","because","been","before","being",
    "below","between","both","but","by","can","can","can't","cannot","could",
    "couldn't","did","didn't","do","does","doesn't","doing","don't","down",
    "during","each","few","for","from","further","had","hadn't","has","hasn't",
    "have","haven't","having","he","he'd","he'll","he's","her","here","here's",
    "hers","herself","him","himself","his","how","how's","i","i'd","i'll",
    "i'm","i've","if","in","into","is","isn't","it","it's","its","itself",
    "let's","me","more","most","mustn't","my","myself","no","nor","not","of",
    "off","on","once","only","or","other","ought","our","ours","ourselves",
    "out","over","own","same","shan't","she","she'd","she'll","she's","should",
    "shouldn't","so","some","such","than","that","that's","the","their",
    "theirs","them","themselves","then","there","there's","these","they",
    "they'd","they'll","they're","they've","this","those","through","to",
    "too","under","until","up","very","was","wasn't","we","we'd","we'll",
    "we're","we've","were","weren't","what","what's","when","when's","where",
    "where's","which","while","who","who's","whom","why","why's","with",
    "won't","would","wouldn't","you","you'd","you'll","you're","you've",
    "your","yours","yourself","yourselves",
    "get"
]

index_settings = {
    "settings": {
        "analysis": {
            "filter": {
                "english_stop": {
                    "type": "stop",
                    "stopwords": stopwords
                },
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english"
                },
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english"
                }
            },
            "analyzer": {
                "english_with_stop_and_stem": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_possessive_stemmer",
                        "english_stop",
                        "english_stemmer"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "english_with_stop_and_stem",
                "search_analyzer": "english_with_stop_and_stem"
            },
            "subtitles": {
                "type": "text",
                "analyzer": "english_with_stop_and_stem",
                "search_analyzer": "english_with_stop_and_stem"
            }
        }
    }
}

# Create the index
index_name = "podcasts"

if es.indices.exists(index=index_name):
    es.indices.delete(index=index_name)

es.indices.create(index=index_name, body=index_settings)
print(f"Index '{index_name}' created successfully")
