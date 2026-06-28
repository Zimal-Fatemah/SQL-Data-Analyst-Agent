# SQL Data Analyst Agent 🚀
A high-performance Natural Language to SQL (NL2SQL) Agent designed for reliable business intelligence. Built using LangChain and LangGraph, this agent transforms complex user questions into structured, accurate insights while maintaining strict output fidelity.

# 💡 The "Data Sandwich" Architecture
Standard LLM wrappers often output "chatty" prose, which is difficult for automated systems to ingest. This agent uses the Data Sandwich pattern, enforcing a rigid Pydantic-based output schema to ensure every response is machine-readable and actionable:

## The Hook (Executive Headline): A concise, high-level insight.

## The Truth (Data Table): Clean, formatted Markdown table.

## The Strategy (Takeaways): Actionable business recommendations.

# 🛠 Tech Stack
## LLM Engine: Groq API (llama-3.3-70b-versatile)

## Security: Read-only database sandboxing

## Validation: Custom Pydantic-based schema enforcement
<img width="1082" height="569" alt="image" src="https://github.com/user-attachments/assets/9c1872b3-dd71-4ba8-b6d9-873753b7c26c" />


# 📋 Key Features
#Structured Output: Strictly enforced Pydantic schemas prevent hallucinations and ensure data format consistency.

#Security-First: Implements a read-only database sandbox to prevent unauthorized data modification.

#Evaluation-Driven: Includes an automated regression test suite (eval/) to validate query accuracy against a gold-standard dataset.

## Installation & Setup
Clone the repository:

Bash
git clone https://github.com/Zimal-Fatemah/SQL-Data-Analyst-Agent.git
cd SQL-Data-Analyst-Agent
Create and activate your virtual environment:

Bash
python -m venv venv
## Windows:
.\venv\Scripts\activate
Install dependencies:

Bash
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Environment Setup:
Create a .env file and add your API keys:

Bash
cp .env.example .env
## Add your GROQ_API_KEY to the .env file
🧪 Quality Assurance (Automated Testing)
To ensure the agent remains accurate as you evolve it, run the built-in regression suite. This script validates that the agent's output structure and logic meet the project's strict requirements:

Bash
.\venv\Scripts\python.exe -m eval.run_eval
