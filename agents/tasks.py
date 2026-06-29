from crewai import Task
from agents.definitions import (
    coordinator_agent,
    research_agent,
    technology_agent,
    decision_maker_agent,
    opportunity_agent,
    email_agent,
    report_agent,
)


def build_tasks(company_name, website):

    task_research = Task(
        description=(
            f"Research the company '{company_name}' (website: {website}). "
            "Find: industry, core products/services, company size, recent news, "
            "and anything else useful for a sales pitch. "
            "Return a structured summary with clear headings."
        ),
        expected_output=(
            "A Markdown summary with sections: Overview, Products/Services, "
            "Industry, Company Size, Recent News."
        ),
        agent=research_agent,
    )

    task_technology = Task(
        description=(
            f"Based on the research about '{company_name}', identify their "
            "technology stack. Look for clues in job postings, GitHub repos, "
            "website source code, and press releases. "
            "List frontend, backend, cloud/infra, databases, and third-party APIs."
        ),
        expected_output=(
            "A JSON object with keys: frontend, backend, cloud, databases, "
            "third_party_apis — each containing a list of technology names."
        ),
        agent=technology_agent,
        context=[task_research],
    )

    task_decision_makers = Task(
        description=(
            f"Find the key decision makers at '{company_name}'. "
            "Target: CEO, CTO, VP Engineering, Head of Product, or similar. "
            "Use only publicly available sources. "
            "For each person provide: name, title, and any public contact info."
        ),
        expected_output=(
            "A Markdown table with columns: Name | Title | LinkedIn URL | Email (if public)."
        ),
        agent=decision_maker_agent,
        context=[task_research],
    )

    task_opportunities = Task(
        description=(
            f"Analyse the research and technology stack for '{company_name}' "
            "and identify the top 3 software/AI/automation opportunities. "
            "For each opportunity: describe the pain point, the solution, "
            "and the potential business impact."
        ),
        expected_output=(
            "A numbered list of 3 opportunities, each with: Pain Point, "
            "Proposed Solution, Business Impact."
        ),
        agent=opportunity_agent,
        context=[task_research, task_technology],
    )

    task_email = Task(
        description=(
            f"Write a personalised cold-outreach email targeting the most "
            f"relevant decision maker at '{company_name}'. "
            "Reference a specific company detail, present ONE clear value "
            "proposition tied to the top opportunity, and include a "
            "low-friction call to action. Keep it under 200 words."
        ),
        expected_output=(
            "A complete email with: Subject line, Greeting, Body, Sign-off."
        ),
        agent=email_agent,
        context=[task_research, task_decision_makers, task_opportunities],
    )

    task_report = Task(
        description=(
            f"Compile all findings for '{company_name}' into a single "
            "Markdown report. Include: company research, tech stack, "
            "decision makers, opportunities, and the outreach email. "
            "Add a header with date and company name."
        ),
        expected_output=(
            "A complete Markdown document with all sections combined."
        ),
        agent=report_agent,
        context=[
            task_research,
            task_technology,
            task_decision_makers,
            task_opportunities,
            task_email,
        ],
    )

    return [
        task_research,
        task_technology,
        task_decision_makers,
        task_opportunities,
        task_email,
        task_report,
    ]