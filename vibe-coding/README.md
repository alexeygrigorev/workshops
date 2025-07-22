# Introduction to Vibe Coding

Watch the workshop here:

<a href="https://www.youtube.com/watch?v=NSMXQk4Axig">
  <img src="https://markdown-videos-api.jorgenkh.no/youtube/NSMXQk4Axig">
</a>


In this workshop, we look at different tools for AI-assisted development

In particular, we cover

- Chat applications
- Coding assistants and IDEs
- Project bootstrapers
- Agents

We will build the Snake game (with JavaScript and React) as an example.
You don't need to know React to take part in this workshop.

<img style="width: 50%;" src="https://github.com/user-attachments/assets/bc732a3c-7f8e-4a2a-ac64-d1834f0f27bd" />


This is a part of our [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp). 


<p align="center">
<a href="https://airtable.com/appJRFiWKHBgmEt70/shrpw7rk55Ewr1jCG"><img src="https://user-images.githubusercontent.com/875246/185755203-17945fd1-6b64-46f2-8377-1011dcb1a444.png" height="50" /></a>
</p>

# Chat Applications

- [ChatGPT](https://chatgpt.com/)
- [Claude](https://claude.ai/)
- [DeepSeek](https://www.deepseek.com/en)
- [Ernie](https://ernie.baidu.com/)
- [Microsoft Copilot](https://copilot.microsoft.com/) (not to be confused with Github Copilot)

Prompt: "implement snake in react"


Helpful, but not convenient for development - require moving back-and-forth
between the chat application and the IDE



# Coding Assistants / IDEs

- [Claude Code](https://www.anthropic.com/claude-code)
- [Github Copilot](https://github.com/features/copilot)
- [Cursor](https://cursor.com/)
- [Pear](https://trypear.ai/)

```bash
npm install -g @anthropic-ai/claude-code
```

# Project bootstapers

- [Bolt](https://bolt.new/)
- [Lovable](https://lovable.dev/)


# Agents

Coding assistants and project bootstrapers both use agents for coding. 
Agents have tools (read files, write files, index codebase, etc) that they
use.

If you want to learn more about Agents and function calling, check 
[this workshop](https://github.com/alexeygrigorev/rag-agents-workshop)
and also [our LLM Zoomcamp course](https://github.com/DataTalksClub/llm-zoomcamp).

Let's take a look at some other agents

- [Antropic's Computer Use](https://github.com/anthropics/anthropic-quickstarts/tree/main/computer-use-demo)
- [PR Agent](https://github.com/qodo-ai/pr-agent)
- And many more

```bash
docker run \
    -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it ghcr.io/anthropics/anthropic-quickstarts:computer-use-demo-latest
```
