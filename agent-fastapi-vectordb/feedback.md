1)
give more info about what the 



first we do it in jupyter - show the steps in readme

then turn jupyter into notebook.py and split it into 

- engine.py with tool calling logic etc
- app.py with fastapi and stream handling 
- regaridng run_agent - right now we do too many things there. can we separate it into multiple parts and implement sse via callbacks or something like that

for ingestion + search. first use minsearch and then switch to qrant in second part. the first part we deploy - wihtout any qdrant 
then show how to swtich to qdrant



