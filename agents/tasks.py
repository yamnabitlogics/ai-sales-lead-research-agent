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
            f"Use the Website Scraper tool to visit '{website}' and read its actual content. "
            f"Research the company '{company_name}' based on what you find. "
            "Find: industry, core products/services, company size, recent news. "
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
            f"Use the Technology Stack Detector tool on '{website}' to find real "
            f"technology signals. Based on the actual detected technologies, "
            "list frontend, backend, cloud/infra, databases, and third-party APIs."
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
            f"Search the web to find the actual current CEO, CTO, VP Engineering, "
            f"or Head of Product at '{company_name}'. "
            f"Use search queries like '{company_name} CEO', '{company_name} CTO LinkedIn', "
            f"'{company_name} leadership team'. "
            "Only report real people found in search results. Do not invent names. "
            "For each person provide: full name, title, and LinkedIn URL if found."
        ),
        expected_output=(
            "A Markdown table: Name | Title | LinkedIn URL | Email (if public). "
            "Minimum 1 person, maximum 5."
        ),
        agent=decision_maker_agent,
        context=[task_research],
    )

    task_opportunities = Task(
        description=(
            f"Based on the real technology stack detected for '{company_name}' "
            "and the company research, identify exactly 3 software or AI opportunities. "
            "If needed, search for recent news about the company's challenges or growth. "
            "For each opportunity be very specific — reference actual technologies "
            "detected, not generic observations."
        ),
        expected_output=(
            "A numbered list of exactly 3 opportunities. Each must have: "
            "Pain Point (specific), Proposed Solution (concrete), Business Impact (quantified where possible)."
        ),
        agent=opportunity_agent,
        context=[task_research, task_technology],
    )

    task_email = Task(
        description=(
            f"Write a personalised cold-outreach email targeting the most "
            f"relevant decision maker found for '{company_name}'. "
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